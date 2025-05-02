import asyncio
import datetime
import uuid

from flask import Flask, jsonify, make_response, redirect, request, session, url_for

import db

app = Flask(__name__)

app.secret_key = uuid.uuid4().hex
app.json.sort_keys = False

weekdays = ["mån", "tis", "ons", "tor", "fre"]


def week_mon2sun(year, week):
    return datetime.datetime.fromisocalendar(
        year, week, 1
    ), datetime.datetime.fromisocalendar(year, week, 5)


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
    monday, sunday = week_mon2sun(year, week)
    w = f"Matsedel vecka {week}, {year} ({monday.month}/{monday.day}-{sunday.month}/{(sunday.day)})"
    weekdict = {
        w: {
            i.capitalize(): (await db.get_food(year, week, weekdays.index(i)))
            for i in weekdays
        },
        "Länkar": [
            f"{baseurl}login",
            f"{baseurl}logout",
            f"{baseurl}register",
            f"{baseurl}week/<vecka>",
        ],
    }
    userdict = {"user": "Not logged in."}  # fallback if user isnt logged in.
    if request.cookies.get("token", None) is not None:
        info = await db.get_info_by_token(
            request.cookies.get("token")
        )  # get user information
        if info is None:
            return redirect("/logout")  # log out if token is invalid
        userdict = {"Username": info[0], "PermissionLevel": db.AuthLevels(info[1]).name}
        if info[1] >= 2:
            userdict["Hantera"] = await db.get_all_users(request.url_root)
        if info[1] >= 1:
            weekdict[w]["Hantera"] = {}  # hantera matsedel
            weekdict[w]["Hantera"]["Mat per dag"] = {
                i: {
                    "Ändra": baseurl + f"mgr/food/{year}/{week}/{n+1}/set",
                    "Radera": baseurl + f"mgr/food/{year}/{week}/{n+1}/del",
                }
                for n, i in enumerate(weekdays)
            }
    weekdict["User"] = userdict

    return jsonify(weekdict)


@app.route("/year/<int:year>")
async def year(year):
    pass


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
    return """
        <form method="post">
            <input type=text name=username placeholder=Användarnamn>
            <input type=password name=password placeholder=Lösenord>
            <input type=submit value=Login>
        </form>
    """  # return html form


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
    return """
        <form method="post">
            <h1>Inloggning</h1>
            <input type=text name=username placeholder="Användarnamn">
            <input type=password name=password placeholder="Lösenord">
            <br>
            <h1>Inbjudan</h1>
            <input type=text name=invitename placeholder="Användarnamn">
            <input type=password name=invitepass placeholder="Lösenord">
            <label>Ny: </label>
            <select id="authlvl" name='authlvl'>
                <option value=0>User</option>
                <option value=1>FoodEditor</option>
                <option value=2>Moderator</option>
                <option value=3>Admin</option>
            </select>
            <br><br>
            <input type=submit value=Registrera>
        </form>
    """  # return html form


@app.route("/mgr/tokrev/<user>")
async def revoke_token(user):
    token = request.cookies.get("token", None)
    if token is None:
        return {"Status": "Failed.", "Reason": "Not logged in."}
    if await hasperms(token, 2):
        tinfo = await db.get_info_by_name(user)
        minfo = await db.get_info_by_token(token)
        if minfo is None:
            return {"Status": "Failed.", "Reason": "Your account does not exist."}
        if tinfo[2] >= minfo[1] and minfo[1] == 2:
            return {
                "Failed to revoke token": f"Target ({user}) is too authorized for you."
            }
        await db.tokenrevoke(tinfo[1])
        return {"Status": "Success!"}
    return {"Status": "Failed.", "Reason": "Invalid Permission"}


@app.route("/mgr/accdel/<user>")
async def delete_account(user):
    token = request.cookies.get("token", None)
    if token is None:
        return {"Status": "Failed.", "Reason": "Not logged in."}
    info = await db.get_info_by_token(token)
    if await hasperms(token, 2) or info[0] == user:
        await db.delete_account(user)
        return {"Status": "Success!"}
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
    return f"""
    <form method="post">
    <h1>Ändra lösenord för '{user}'</h1>
    <input type=password name=oldpassword placeholder="Gammalt Lösenord">
    <input type=password name=newpassword placeholder="Nytt Lösenord" autocomplete="new-password">
    <input type=submit value=Ok>
    </form>
"""


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
