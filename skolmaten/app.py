import datetime
import json
import os
import time

from dotenv import load_dotenv
from flask import (
    Blueprint,
    Response,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from . import db

config = load_dotenv()
app = Blueprint(
    "main", __name__, static_url_path=os.environ.get("ROOT", "/") + "static"
)
os.environ["TZ"] = "Europe/London"
time.tzset()

weekdays = ["mån", "tis", "ons", "tor", "fre"]
weekdays_en = ["mon", "tue", "wed", "thu", "fri"]


def week_mon2sun(year, week):
    r = [
        datetime.datetime.fromisocalendar(year, week, 1),
        datetime.datetime.fromisocalendar(year, week, 5),
    ]
    return r


def is_week_in_next_year(year, week_num):
    max_weeks = datetime.date(year, 12, 28).isocalendar()[1]
    return week_num > max_weeks


@app.route("/")
def root():
    week = datetime.datetime.now().isocalendar()[1]
    return redirect(url_for("main.week", week=week))


async def hasperms(token, perms):
    if token is None:
        return False
    info = await db.get_info_by_token(token)
    if info[1] >= perms:
        return True
    return False


# for dynamic urls in css (used for font)
@app.route("/static/style.css")
def dynamic_css():
    css = render_template("style.css")
    return Response(css, mimetype="text/css")


@app.route("/week/<int:week>")
async def week(week):
    baseurl = request.url_root + url_for("main.root")[1:]
    year = request.args.get("year", type=int)
    curweek = datetime.datetime.now().isocalendar()[1]
    token = request.cookies.get("token")
    if year is None:
        year = datetime.datetime.now().year
    if is_week_in_next_year(year, week):
        return redirect(url_for("main.week", week=1, year=year + 1))
    if week <= 0:
        return redirect(
            url_for(
                "main.week",
                week=datetime.date(year - 1, 12, 28).isocalendar()[1],
                year=year - 1,
            )
        )
    m2s = week_mon2sun(year, week)
    monday = m2s[0]
    links = [
        f"login - Logga in",
        f"register - Registrera nytt konto",
        f"week/{curweek} - Matsedel för vecka {curweek}",
        f"year/{year} - Matsedel för år {year}",
    ]
    userdict = {
        "Username": "anonymous",
        "PermissionLevel": 0,
        "Display": "Anonymous",
    }  # fallback if user isnt logged in.
    if token:
        info = await db.get_info_by_token(token)
        if not info:
            return redirect(url_for("main.logout"))

        username, permission, display = info
        userdict = {
            "Username": username,
            "PermissionLevel": permission,
            "Display": display,
        }

        if permission >= 2:
            userdict["Hantera"] = await db.get_all_users(baseurl)
        else:
            userdict["Hantera"] = await db.get_self(baseurl, username)
        links.insert(
            1,
            "logout - Logga ut",
        )
        links.append(f"mgr/edtdsp/{userdict['Username']} - Byt namn")

    if userdict["Username"] != "Anonymous":
        links.append(f"mgr/edtpwd/{userdict['Username']} - Ändra lösenord")
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
    baseurl = request.url_root + url_for("main.root")[1:]
    week = datetime.date.today().isocalendar().week
    userdict = {"Username": "Anonymous", "PermissionLevel": 0}
    token = request.cookies.get("token")

    links = [
        "login - Logga in",
        "register - Registrera nytt konto",
        f"week/{week} - Matsedel för vecka {week}",
        f"year/{year} - Matsedel för år {year}",
    ]
    if token:
        info = await db.get_info_by_token(token)
        if not info:
            return redirect(url_for("main.logout"))

        username, permission, display = info
        userdict = {"Username": username, "PermissionLevel": permission}

        if permission >= 2:
            userdict["Hantera"] = await db.get_all_users(baseurl)
        else:
            userdict["Hantera"] = await db.get_self(baseurl, username)
        links.insert(
            1,
            "logout - Logga ut",
        )
        links.append(f"mgr/edtdsp/{userdict['Username']} - Byt namn")

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
            resp = make_response(redirect(url_for("main.root")))
            resp.set_cookie(
                "token",
                await db.signin(
                    request.form["username"].lower(), request.form["password"]
                ),
            )
            return resp
        except Exception as e:
            return {"Failed to Log In": str(e)}
    return render_template("login.html")


@app.route("/logout")
async def logout():
    resp = make_response(redirect(url_for("main.root")))
    resp.set_cookie("token", "", expires=0)  # properly clear the token from cookies.
    return resp


@app.route("/register", methods=["GET", "POST"])
async def register():
    if request.method == "POST":
        try:
            await db.register(
                request.form["username"],
                request.form["password"],
                0,
            )

            resp = make_response(redirect(url_for("main.root")))
            resp.set_cookie(
                "token",
                await db.signin(
                    request.form["username"].lower(), request.form["password"]
                ),
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
        return redirect(url_for("main.root"))
    return {"Status": "Failed.", "Reason": "Invalid Permission"}


@app.route("/mgr/accdel/<user>")
async def delete_account(user):
    token = request.cookies.get("token", None)
    if token is None:
        return {"Status": "Failed.", "Reason": "Not logged in."}
    info = await db.get_info_by_token(token)
    if await hasperms(token, 2) or info[0] == user:
        await db.delete_account(user)
        return redirect(url_for("main.root"))
    return {"Status": "Failed.", "Reason": "Unauthorized."}


@app.route("/mgr/edtdsp/<user>", methods=["GET", "POST"])
async def edit_display_name(user):
    if request.method == "POST":
        try:
            token = request.cookies.get("token", None)
            if token is None:
                raise Exception("Unauthorized")
            info = await db.get_info_by_token(token)
            if await hasperms(token, 2) or info[0] == user:
                await db.changedisplay(user, request.form.get("display"))

            return redirect(url_for("main.root"))
        except Exception as e:
            return {"Status": "Failed.", "Reason": str(e)}
    return render_template("changedisplay.html")


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
        return redirect(url_for("main.root"))
    return {"Status": "Failed.", "Reason": "Invalid permissions."}


@app.route("/mgr/edtpwd/<string:user>", methods=["GET", "POST"])
async def edit_password(user):
    if request.method == "POST":
        try:
            await db.change_password(
                user, request.form["oldpassword"], request.form["newpassword"]
            )
            return redirect(url_for("main.root"))
        except Exception as e:
            return {"Status": "Failed.", "Reason": str(e)}
    return render_template("changepassword.html")


@app.route("/mgr/food/<int:year>/<int:week>/<int:weekday>/set", methods=["GET", "POST"])
async def editfoodforday(year, week, weekday):
    if request.method == "POST":
        try:
            if await hasperms(request.cookies.get("token", None), 1):
                await db.set_food(year, week, weekday, request.form["value"])
            return redirect(url_for("main.week", week=week))
        except Exception as e:
            return {
                f"Failed to set Food for {datetime.date.fromisocalendar(year,week,weekday)}": str(
                    e
                )
            }
    return render_template(
        "editfood.html", day=datetime.date.fromisocalendar(year, week, weekday)
    )


@app.route("/mgr/food/<int:year>/<int:week>/<int:weekday>/del")
async def deletefoodforday(year, week, weekday):
    try:
        if await hasperms(request.cookies.get("token", None), 1):
            await db.set_food(year, week, weekday, "")
        return redirect(url_for("main.week", week=week))
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
            token = request.cookies.get("token")
            if not token:
                return {"error": "Invalid Permissions"}, 403

            file = request.files.get("json")
            if not file:
                return {"error": "No file uploaded"}, 400

            j = json.load(file.stream)
            for year, weeks in j.items():
                for week, days in weeks.items():
                    for day, value in days.items():
                        day_short = day[
                            :3
                        ].lower()  # truncate to 3 letters, just in case so the app doesnt shit itself
                        if day_short not in weekdays_en:
                            continue
                        weekday = weekdays_en.index(day_short) + 1
                        await db.set_food(year, week, weekday, value)

            return redirect(url_for("main.root"))

        except Exception as e:
            return {"error": f"Failed to import food: {str(e)}"}, 500

    return render_template("import.html")


@app.route("/comments/day/<int:year>/<int:week>/<int:weekday>")
async def comments(year, week, weekday):
    commlist = await db.getcomments(year, week, weekday)
    return render_template(
        "comments.html",
        timestr=datetime.datetime.fromisocalendar(year, week, weekday + 1).strftime(
            "%a %d %b"
        ),
        year=year,
        week=week,
        weekday=weekday,
        comments=commlist,
    )


@app.route("/comments/add/<int:year>/<int:week>/<int:weekday>", methods=["GET", "POST"])
async def addcomment(year, week, weekday):
    if request.method == "POST":
        try:
            token = request.cookies.get("token")
            if not token:
                raise Exception("Unauthorized")
            info = await db.get_info_by_token(token)
            if info is None:
                raise Exception("Unauthorized")
            value = str(request.form.get("value", "")).strip()
            if not value:
                raise Exception("Invalid comment")
            await db.addcomment(year, week, weekday, info[0], value, info[2])
            return redirect(
                url_for("main.comments", year=year, week=week, weekday=weekday)
            )
        except Exception as e:
            return {"error": f"Failed to add comment: {str(e)}"}, 500
    return render_template(
        "addcommentmodal.html",
        timestr=datetime.datetime.fromisocalendar(year, week, weekday + 1).strftime(
            "%a %d %b"
        ),
    )
