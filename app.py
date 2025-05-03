import asyncio
import datetime
import json
import uuid

from flask import (
    Flask,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

import db

app = Flask(__name__)

app.secret_key = uuid.uuid4().hex
app.json.sort_keys = False

weekdays = ["mån", "tis", "ons", "tor", "fre"]
weekdays_en = ["mon", "tue", "wed", "thu", "fri"]


def week_mon2sun(year, week):
    r = [
        datetime.datetime.fromisocalendar(year, week, 1),
        datetime.datetime.fromisocalendar(year, week, 5),
    ]
    return r


@app.route("/")
def root():
    week = datetime.datetime.now().isocalendar()[1]
    return redirect(f"/week/{week}")


async def hasperms(token, perms):
    if token is None:
        return False
    info = await db.get_info_by_token(token)
    if info[1] >= perms:
        return True
    return False


@app.route("/week/<int:week>")
async def week(week):
    baseurl = request.url_root
    year = request.args.get("year", type=int)
    if year is None:
        year = datetime.datetime.now().year
    m2s = week_mon2sun(year, week)
    monday = m2s[0]
    sunday = m2s[1]
    w = f"Matsedel vecka {week}, {year} ({monday.month}/{monday.day}-{sunday.month}/{(sunday.day)})"
    links = [
        f"login - Logga in",
        f"logout - Logga ut",
        f"register - Registrera nytt konto",
        f"week/{week} - Matsedel för vecka {week}",
        f"year/{year} - Matsedel för år {year}",
    ]
    userdict = {
        "Username": "Anonymous",
        "PermissionLevel": 0,
    }  # fallback if user isnt logged in.
    if request.cookies.get("token", None) is not None:
        info = await db.get_info_by_token(
            request.cookies.get("token")
        )  # get user information
        if info is None:
            return redirect("/logout")  # log out if token is invalid
        userdict = {
            "Username": info[0],
            "PermissionLevel": info[1],
        }
        if info[1] >= 2:
            userdict["Hantera"] = await db.get_all_users(request.url_root)
        else:
            userdict["Hantera"] = await db.get_self(
                request.url_root, userdict["Username"]
            )
        links.append(f"mgr/edtpwd/{info[0]} - Ändra lösenord")
        if userdict["PermissionLevel"] >= 1:
            links.append(f"mgr/food/import - Importera matsedel från JSON")

    return render_template(
        "week.html",
        weekdata=monday,
        week=week,
        year=year,
        weekday=weekdays,
        schema=[
            [
                baseurl + f"mgr/food/{year}/{week}/{i+1}/",
                await db.get_food(year, week, i),
            ]
            for i in range(0, 5)
        ],
        links=links,
        baseurl=baseurl,
        userdict=userdict,
        str=str,
        configdict=userdict.get("Hantera", {}),
        list=list,
        datetime=datetime.datetime,
    )


@app.route("/year/<int:year>")
async def yearplan(year):
    baseurl = request.url_root
    week = datetime.date.today().isocalendar().week
    userdict = {"Username": "Anonymous", "PermissionLevel": 0}
    token = request.cookies.get("token")

    if token:
        info = await db.get_info_by_token(token)
        if not info:
            return redirect("/logout")

        username, permission = info
        userdict = {"Username": username, "PermissionLevel": permission}

        if permission >= 2:
            userdict["Hantera"] = await db.get_all_users(baseurl)
        else:
            userdict["Hantera"] = await db.get_self(baseurl, username)

    links = [
        "login - Logga in",
        "logout - Logga ut",
        "register - Registrera nytt konto",
        f"week/{week} - Matsedel för vecka {week}",
        f"year/{year} - Matsedel för år {year}",
    ]

    if userdict["Username"] != "Anonymous":
        links.append(f"mgr/edtpwd/{userdict['Username']} - Ändra lösenord")
    if userdict["PermissionLevel"] >= 1:
        links.append(f"mgr/food/import - Importera matsedel från JSON")

    return render_template(
        "year.html",
        year=year,
        weekday=weekdays,
        schema=await db.get_food_year(year),
        links=links,
        baseurl=baseurl,
        userdict=userdict,
        configdict=userdict.get("Hantera", {}),
        str=str,
        list=list,
        datetime=datetime.datetime,
    )


@app.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        try:
            resp = make_response(redirect("/"))
            resp.set_cookie(
                "token",
                await db.signin(request.form["username"], request.form["password"]),
            )
            return resp
        except Exception as e:
            return {"Failed to Log In": str(e)}
    return render_template("login.html")


@app.route("/logout")
async def logout():
    resp = make_response(redirect("/"))
    resp.set_cookie("token", "", expires=0)  # properly clear the token from cookies.
    return resp


@app.route("/register", methods=["GET", "POST"])
async def register():
    if request.method == "POST":
        try:
            managertoken = await db.signin(
                request.form["invitename"], request.form["invitepass"]
            )
            managerpermission = (await db.get_info_by_token(managertoken))[1]
            if managerpermission >= int(db.AuthLevels.Moderator.value):
                if int(request.form["authlvl"]) >= managerpermission:
                    raise Exception(
                        "Can't create user with higher permission than inviter!"
                    )
                await db.register(
                    request.form["username"],
                    request.form["password"],
                    int(request.form["authlvl"]),
                )
            else:
                raise Exception("Invalid permissions for inviter.")

            resp = make_response(redirect("/"))
            resp.set_cookie(
                "token",
                await db.signin(request.form["username"], request.form["password"]),
            )  # log in after registering
            return resp
        except Exception as e:
            return {"Failed to Log In": str(e)}
    return render_template("register.html")


@app.route("/mgr/tokrev/<user>")
async def revoke_token(user):
    token = request.cookies.get("token", None)
    if token is None:
        return {"Status": "Failed.", "Reason": "Not logged in."}
    info = await db.get_info_by_token(token)
    if await hasperms(token, 2) or info[0] == user:
        tinfo = await db.get_info_by_name(user)
        minfo = await db.get_info_by_token(token)
        if minfo is None:
            return {"Status": "Failed.", "Reason": "Your account does not exist."}
        if tinfo[2] >= minfo[1] and minfo[1] == 2:
            return {
                "Failed to revoke token": f"Target ({user}) is too authorized for you."
            }
        await db.tokenrevoke(tinfo[1])
        return redirect("/")
    return {"Status": "Failed.", "Reason": "Invalid Permission"}


@app.route("/mgr/accdel/<user>")
async def delete_account(user):
    token = request.cookies.get("token", None)
    if token is None:
        return {"Status": "Failed.", "Reason": "Not logged in."}
    info = await db.get_info_by_token(token)
    if await hasperms(token, 2) or info[0] == user:
        await db.delete_account(user)
        return redirect("/")
    return {"Status": "Failed.", "Reason": "Unauthorized."}


@app.route("/mgr/edtprm/<string:user>/<int:permlevel>")
async def edit_permission(user, permlevel):
    token = request.cookies.get("token", None)
    if token is None:
        return {"Status": "Failed.", "Reason": "Not logged in."}
    permission = await db.get_info_by_token(token)
    if permission is None:
        return {"Status": "Failed.", "Reason": "Invalid Account."}
    permission = permission[1]
    if permission >= int(db.AuthLevels.Moderator.value):
        if permlevel >= permission:
            return {
                "Status": "Failed.",
                "Reason": "Can't assign higher or equal permission level.",
            }
        await db.edit_permission(user, permlevel)
        return {"Status": "Success!"}
    return {"Status": "Failed.", "Reason": "Invalid permissions."}


@app.route("/mgr/edtpwd/<string:user>", methods=["GET", "POST"])
async def edit_password(user):
    if request.method == "POST":
        try:
            await db.change_password(
                user, request.form["oldpassword"], request.form["newpassword"]
            )
            return redirect("/")
        except Exception as e:
            return {"Status": "Failed.", "Reason": str(e)}
    return render_template("changepassword.html")


@app.route("/mgr/food/<int:year>/<int:week>/<int:weekday>/set", methods=["GET", "POST"])
async def editfoodforday(year, week, weekday):
    if request.method == "POST":
        try:
            if await hasperms(request.cookies.get("token", None), 1):
                await db.set_food(year, week, weekday, request.form["value"])
            return redirect(f"/week/{week}")
        except Exception as e:
            return {
                f"Failed to set Food for {datetime.date.fromisocalendar(year,week,weekday)}": str(
                    e
                )
            }
    return f"""
    <form method="post">
        <input type=text name=value placeholder="Mat {datetime.date.fromisocalendar(year,week,weekday)}">
        <input type=submit value=Ok>
    </form>
"""


@app.route("/mgr/food/<int:year>/<int:week>/<int:weekday>/del")
async def deletefoodforday(year, week, weekday):
    try:
        if await hasperms(request.cookies.get("token", None), 1):
            await db.set_food(year, week, weekday, "")
        return redirect(f"/week/{week}")
    except Exception as e:
        return {
            f"Failed to set Food for {datetime.date.fromisocalendar(year,week,weekday)}": str(
                e
            )
        }


@app.route("/mgr/food/import", methods=["GET", "POST"])
async def importfoodjson():
    if request.method == "POST":
        try:
            token = request.cookies.get("token", None)
            if token is None:
                raise Exception("Invalid Permissions")
            file = request.files["json"]
            if file:
                j = json.load(file)
                for year, weeks in j.items():
                    for week, days in weeks.items():
                        for day, value in days.items():
                            print(day[0:3].lower(), weekdays_en.index(day[0:3].lower()))
                            weekday = int(weekdays_en.index(day[0:3].lower())) + 1
                            await db.set_food(year, week, weekday, value)
                        print(year, week, days)
            return redirect("/")
        except Exception as e:
            return {"Failed to import food": str(e)}
    return render_template("import.html")
