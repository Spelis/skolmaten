import asyncio
import datetime
import uuid
from enum import Enum
from sqlite3 import connect

import aiosqlite
from jose.jwt import decode, encode

secret = uuid.uuid4().hex


class AuthLevels(Enum):
    User = 0
    FoodEditor = 1
    Moderator = 2
    Admin = 3


weekdays = ["mon", "tue", "wed", "thu", "fri"]


def generate_jwt_token(name: str) -> str:
    payload = {
        "sub": name,
        "iat": datetime.datetime.now(datetime.timezone.utc).timestamp(),
    }
    return encode(payload, secret, algorithm="HS256")


async def create_schema():
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                token TEXT,
                name TEXT PRIMARY KEY UNIQUE,
                pass TEXT NOT NULL,
                authlvl INTEGER DEFAULT 0
            );
        """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS weeks (
                week INT,
                year INT,
                mon TEXT,
                tue TEXT,
                wed TEXT,
                thu TEXT,
                fri TEXT
            );
        """
        )
        await db.commit()

        async with db.execute(
            "SELECT 1 FROM users WHERE name = ?", ("adminacc",)
        ) as cursor:
            exists = await cursor.fetchone()

        if not exists:
            await register("adminacc", "adminpassword", int(AuthLevels.Admin.value))


async def signin(username: str, passwd: str):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT * FROM users WHERE name = ?", (username,)
        ) as cursor:
            user = await cursor.fetchone()

        if user is None or passwd != user[2]:
            raise Exception("Invalid credentials")

        tok = generate_jwt_token(user[1])

        await db.execute("UPDATE users SET token = ? WHERE name = ?;", (tok, user[1]))
        await db.commit()

        return tok


async def register(username: str, passwd: str, authlvl):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE name = ?", (username,)
        ) as cursor:
            exists = await cursor.fetchone()

        if exists:
            raise Exception("User already exists")

        await db.execute(
            "INSERT INTO users (token, name, pass, authlvl) VALUES (?, ?, ?, ?)",
            (generate_jwt_token(username), username, passwd, authlvl),
        )
        await db.commit()


async def get_info_by_token(token):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT name,authlvl FROM users WHERE token = ?", (token,)
        ) as cursor:
            row = await cursor.fetchone()
            return (row[0], row[1]) if row else None


async def get_all_users(baseurl: str):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            r = {}
            for row in rows:
                r[row[1]] = {
                    "token": row[0],
                    "name": row[1],
                    "pass": row[2],
                    "auth": {row[3]: AuthLevels(row[3]).name},
                    "revoke_token": baseurl + f"mgr/tokrev/{row[1]}",
                    "delete_account": baseurl + f"mgr/accdel/{row[1]}",
                    "change_password": baseurl + f"mgr/edtpwd/{row[1]}",
                    "change_permission": {
                        AuthLevels(i).name: baseurl + f"mgr/edtprm/{row[1]}/{i}"
                        for i in range(4)
                    },
                }

            return r


async def get_self(baseurl: str, name: str):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT pass,name,authlvl FROM users WHERE name = ?", (name,)
        ) as cursor:
            rows = await cursor.fetchall()
            r = {}
            for row in rows:
                r[row[1]] = {
                    "name": row[1],
                    "pass": row[0],
                    "auth": {row[2]: AuthLevels(row[2]).name},
                    "revoke_token": baseurl + f"mgr/tokrev/{row[1]}",
                    "delete_account": baseurl + f"mgr/accdel/{row[1]}",
                    "change_password": baseurl + f"mgr/edtpwd/{row[1]}",
                    "change_permission": {
                        AuthLevels(i).name: baseurl + f"mgr/edtprm/{row[1]}/{i}"
                        for i in range(4)
                    },
                }

            return r


async def get_info_by_name(name):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT pass,token,authlvl FROM users WHERE name = ?", (name,)
        ) as cursor:
            return await cursor.fetchone()


async def tokenrevoke(token):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET token = ? WHERE token = ?", (None, token))
        await db.commit()


async def set_food(year, week, day, value):
    col = weekdays[day - 1] if 0 <= day - 1 < len(weekdays) else None
    if not col:
        raise ValueError(
            "Invalid day index"
        )  # check so we dont provide weekday 15 (doesn't exist)

    async with aiosqlite.connect("database.db") as db:
        # try update
        cursor = await db.execute(
            f"UPDATE weeks SET {col} = ? WHERE week = ? AND year = ?",
            (value, week, year),
        )
        await db.commit()

        if cursor.rowcount == 0:
            # insert empty row with value in right column
            values = [""] * len(weekdays)
            values[day] = value
            await db.execute(
                f"INSERT INTO weeks (year, week, {','.join(weekdays)}) VALUES (?, ?, {','.join(['?']*len(weekdays))})",
                (year, week, *values),
            )
            await db.commit()


async def get_food(year, week, day):
    async with aiosqlite.connect("database.db") as db:
        day = weekdays[day]
        async with db.execute(
            f"SELECT {day} FROM weeks WHERE week = ? and year = ?", (week, year)
        ) as cursor:
            val = await cursor.fetchone()
            return val[0] if val else ""


async def get_food_year(year):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT week, mon, tue, wed, thu, fri FROM weeks WHERE year = ?", (year,)
        ) as cursor:
            existing = {row[0]: row[1:] for row in await cursor.fetchall()}

    total_weeks = datetime.date(year, 12, 28).isocalendar()[1]
    result = []
    for week in range(1, total_weeks + 1):
        date = datetime.datetime.fromisocalendar(year, week, 1)
        days = list(existing.get(week, [""] * 5))
        result.append(
            {
                "date": date,
                "week": week,
                "days": [{"text": days[i], "day": i + 1} for i in range(5)],
            }
        )
    return result


async def delete_account(name):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("DELETE FROM users WHERE name = ?", (name,))
        await db.commit()


async def edit_permission(name, perm):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET authlvl = ? WHERE name = ?", (perm, name))
        await db.commit()


async def change_password(name, old, new):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT pass FROM users WHERE name = ?", (name,)
        ) as cursor:
            current = await cursor.fetchone()

        if not current or current[0] != old:
            raise Exception("Incorrect current password.")
        await db.execute("UPDATE users SET pass = ? WHERE name = ?", (new, name))
        await db.commit()


def init_app():
    asyncio.run(create_schema())
