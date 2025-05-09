import datetime
import json
import os
import re
import time
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Blueprint,
    Response,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import db

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
    today = datetime.date.today()
    now = datetime.datetime.now()

    # If it's Saturday, Sunday, or Friday afternoon (12:00 PM onwards)
    if today.isoweekday() >= 6 or (today.isoweekday() == 5 and now.hour >= 12):
        today += datetime.timedelta(days=8 - today.isoweekday())

    week = today.isocalendar()[1]
    year = today.year  # Get the current year
    return redirect(url_for("main.week", year=year, week=week))


async def hasperms(token, perms):
    if token is None:
        return False
    info: dict = await db.user_by_token(token)
    if not info:
        return False
    if info["auth"] >= perms:
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
    year = request.args.get("year", type=int, default=datetime.datetime.now().year)
    curweek = datetime.datetime.now().isocalendar()[1]
    token = request.cookies.get("token")
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
    monday = datetime.datetime.fromisocalendar(year, week, 1)

    links = [
        f"login - Logga in",
        f"register - Registrera nytt konto",
        f"week/{curweek} - Matsedel för vecka {curweek}",
        f"year/{year} - Matsedel för år {year}",
    ]
    i = await db.id_by_token(str(token))
    if await hasperms(token, 2):
        userdict = await db.get_all_users()
    elif i is None:
        userdict = [{"name": "null", "auth": -1, "id": -1, "display": "Null"}]
    elif token is not None:
        userdict = [await db.user_by_id(int(i))]
        i = 0
    else:
        userdict = []  # should never happen but just in case

    if token and (i is not None):
        links.append(f"mgr/edtpwd/{i} - Ändra lösenord")
        links.insert(
            1,
            "logout - Logga ut",
        )
        links.append(f"mgr/edtdsp/{i} - Byt namn")
    if await hasperms(token, 1):
        links.append(f"mgr/food/import - Importera matsedel från JSON")

    comlen = [len(await db.getcomments(year, week, i)) for i in range(5)]
    foodplan = []
    for weekday in range(5):
        foodplan.append(
            [
                url_for(
                    "main.editfoodforday", year=year, week=week, weekday=weekday + 1
                ),
                await db.get_food(year, week, weekday),
            ]
        )

    return render_template(
        "week.html",
        year=year,
        week=week,
        weekday=weekdays,
        curweek=curweek,
        userdict=userdict,
        loginid=i if i is not None else -1,
        baseurl=baseurl,
        str=str,
        list=list,
        int=int,
        datetime=datetime.datetime,
        weekdata=monday,
        schema=foodplan,
        comlen=comlen,
        links=links,
    )


@app.route("/year/<int:year>")
async def yearplan(year):
    baseurl = request.url_root + url_for("main.root")[1:]
    curweek = datetime.datetime.now().isocalendar()[1]
    token = request.cookies.get("token")

    links = [
        "login - Logga in",
        "register - Registrera nytt konto",
        f"week/{curweek} - Matsedel för vecka {curweek}",
        f"year/{year} - Matsedel för år {year}",
    ]

    i = await db.id_by_token(str(token))
    if await hasperms(token, 2):
        userdict = await db.get_all_users()
    elif i is None:
        userdict = [{"name": "null", "auth": -1, "id": -1, "display": "Null"}]
    elif token is not None:
        userdict = [await db.user_by_id(int(i))]
        i = 0
    else:
        userdict = []

    if token and (i is not None):
        links.append(f"mgr/edtpwd/{i} - Ändra lösenord")
        links.insert(1, "logout - Logga ut")
        links.append(f"mgr/edtdsp/{i} - Byt namn")
    if await hasperms(token, 1):
        links.append(f"mgr/food/import - Importera matsedel från JSON")

    comlen = []
    for week in range(1, 53):  # ISO weeks are 1–52 (or 53)
        week_counts = []
        for day in range(5):  # Mon–Fri
            comments = await db.getcomments(year, week, day)
            week_counts.append(len(comments))
        comlen.append(week_counts)

    return render_template(
        "year.html",
        year=year,
        weekday=weekdays,
        schema=await db.get_food_year(year),
        links=links,
        userdict=userdict,
        loginid=i if i is not None else -1,
        baseurl=baseurl,
        str=str,
        list=list,
        datetime=datetime.datetime,
        comlen=comlen,
        usercount=range(len(userdict)),
    )


def errorpage(code: int, message: str):
    return render_template("error.html", code=code, message=message), int(code)


def correct_loginname(username: str):
    return re.sub(r"[^a-z0-9_]", "", username.lower())


@app.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        try:
            resp = make_response(redirect(url_for("main.root")))
            resp.set_cookie(
                "token",
                await db.signin(
                    correct_loginname(request.form["username"]),
                    request.form["password"],
                ),
            )
            return resp
        except Exception as e:
            return errorpage(403, "Forbidden: Invalid Credentials")
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
                    correct_loginname(request.form["username"]),
                    request.form["password"],
                ),
            )  # log in after registering
            return resp
        except Exception as e:
            return errorpage(403, "Forbidden: Invalid Credentials")
    return render_template("register.html")


@app.route("/mgr/tokrev/<int:id>")
async def revoke_token(id):
    token = request.cookies.get("token", None)
    if token is None:
        return errorpage(401, "Ej Inloggad")
    mid = await db.id_by_token(token)  # my id
    if mid is None:
        return errorpage(403, "Invalid inloggning")
    if await hasperms(token, 2) or mid == id:
        await db.tokenrevoke(token)
    return redirect(url_for("main.root"))


@app.route("/mgr/accdel/<int:id>")
async def delete_account(id):
    if id == 0:
        return errorpage(403, "Admin is protected!")
    token = request.cookies.get("token", None)
    if token is None:
        return errorpage(403, "Unauthorized")
    info = await db.id_by_token(token)
    if await hasperms(token, 2) or info == id:
        await db.delete_account(id)
        return redirect(url_for("main.root"))
    return {"Status": "Failed.", "Reason": "Unauthorized."}


@app.route("/mgr/edtdsp/<id>", methods=["GET", "POST"])
async def edit_display_name(id):
    if request.method == "POST":
        try:
            token = request.cookies.get("token", None)
            if token is None:
                raise errorpage(401, "Unauthorized")
            info = await db.user_by_token(token)
            if await hasperms(token, 2) or info["id"] == id:
                await db.changedisplay(id, request.form.get("display"))

            return redirect(url_for("main.root"))
        except Exception as e:
            return {500, "Possible Internal Server Error"}
    return render_template("changedisplay.html", id=id)


@app.route("/mgr/edtlgn/<id>", methods=["POST"])
async def edit_login(id):
    try:
        token = request.cookies.get("token", None)
        if token is None:
            raise Exception("Unauthorized")
        info = await db.user_by_token(token)
        if await hasperms(token, 2) or info["id"] == id:
            await db.editlogin(id, request.form.get("display"))

        return redirect(url_for("main.root"))
    except Exception as e:
        return {"Status": "Failed.", "Reason": str(e)}


@app.route("/mgr/edtprm/<int:id>/<int:permlevel>")
async def edit_permission(id: int, permlevel: int):
    token = request.cookies.get("token", None)
    if token is None:
        return errorpage(401, "Not logged in")
    mid = await db.id_by_token(token)
    if mid is None:
        return errorpage(401, "Invalid Token")
    info = await db.user_by_id(mid)
    permission = info["auth"]
    if permission >= int(db.AuthLevels.Moderator.value):
        if permlevel >= permission:
            return errorpage(
                403,
                "Can't assign higher or equal permission level.",
            )
        await db.edit_permission(id, permlevel)
        return redirect(url_for("main.root"))
    return errorpage(403, "Invalid Permissions")


@app.route("/mgr/edtpwd/<int:id>", methods=["GET", "POST"])
async def edit_password(id):
    if request.method == "POST":
        try:
            await db.change_password(
                id, request.form["oldpassword"], request.form["newpassword"]
            )
            return redirect(url_for("main.root"))
        except Exception as e:
            return errorpage(400, str(e))
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
    token = request.cookies.get("token")
    hasperm = await hasperms(token, 0)
    ismod = await hasperms(token, 2)
    session["back"] = request.url
    return render_template(
        "comments.html",
        timestr=datetime.datetime.fromisocalendar(year, week, weekday + 1).strftime(
            "%a %d %b"
        ),
        year=year,
        week=week,
        weekday=weekday,
        comments=commlist,
        hasperm=hasperm,
        ismod=ismod,
    )


@app.route("/comments/all")
async def allcomments():
    commlist = await db.getallcomments()
    return commlist


@app.route("/comments/add/<int:year>/<int:week>/<int:weekday>", methods=["POST"])
async def addcomment(year, week, weekday):
    if request.method == "POST":
        token = request.cookies.get("token")
        if not token:
            return errorpage(401, "Not logged in")
        info = await db.user_by_token(token)
        if info is None:
            return errorpage(403, "Unauthorized")
        value = str(request.form.get("value", "")).strip()
        if not value:
            return errorpage(400, "No comment")
        await db.addcomment(year, week, weekday, value, info["id"])
        return redirect(url_for("main.comments", year=year, week=week, weekday=weekday))


@app.route("/comments/del/<int:id>")
async def delcomment(id):
    token = request.cookies.get("token")
    info = await db.user_by_token(token)
    if not token:
        return errorpage(401, "Unauthorized")
    user = (await db.get_author_by_comment_id(id)).split(":")[0]
    comment = await db.comment_by_id(id)
    if comment["comment"] == "<Deleted>":
        fr = True
    else:
        fr = False
    print(fr)
    if await hasperms(token, 2) or info["name"] == user:
        await db.delcomment(id, fr)
        return redirect(url_for("main.root"))
