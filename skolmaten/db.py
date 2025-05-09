import asyncio
import datetime
import uuid
from enum import Enum

import aiosqlite
from jose.jwt import decode, encode
from passlib.context import CryptContext

secret = uuid.uuid4().hex


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthLevels(Enum):
    Null = -1
    User = 0
    FoodEditor = 1
    Moderator = 2
    Admin = 3


weekdays = ["mon", "tue", "wed", "thu", "fri"]


def hash_password(password: str) -> str:
    """Hash a password with a salt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


async def get_next_user_id():
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT MAX(id) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] or 0


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
                id INT PRIMARY KEY UNIQUE,
                name TEXT UNIQUE NOT NULL,
                pass TEXT NOT NULL,
                authlvl INTEGER DEFAULT 0,
                display TEXT,
                deleted INT DEFAULT 0
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
        await db.execute(
            """
                CREATE TABLE IF NOT EXISTS comments (
                week INT,
                year INT,
                day INT,
                id INT PRIMARY KEY,
                value TEXT,
                author INT
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
            "SELECT name, pass FROM users WHERE name = ?", (username,)
        ) as cursor:
            user = await cursor.fetchone()

        if user is None or not verify_password(passwd, user[1]):
            raise Exception("Invalid credentials")

        tok = generate_jwt_token(user[1])

        await db.execute("UPDATE users SET token = ? WHERE name = ?;", (tok, user[0]))
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
            "INSERT INTO users (token, name, pass, authlvl, display, id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "",
                username.lower(),
                hash_password(passwd),
                authlvl,
                username,
                await get_next_user_id(),
            ),
        )
        await db.commit()


async def id_by_token(token: str) -> int | None:
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT id FROM users WHERE token = ?", (token,)
        ) as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row is not None else None


async def get_all_users():
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT id,name,display,authlvl,deleted FROM users"
        ) as cursor:
            rows = await cursor.fetchall()
            r = []
            for row in rows:
                r.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "display": row[2],
                        "auth": row[3],
                        "authstr": AuthLevels(row[3]).name,
                        "deleted": bool(row[4]),
                    }
                )

            return r


async def user_by_token(t: str):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT id,name,display,authlvl,deleted FROM users WHERE token = ?", (t,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            r = {
                "id": row[0],
                "name": row[1],
                "display": row[2],
                "auth": row[3],
                "authstr": AuthLevels(row[3]).name,
                "deleted": bool(row[4]),
            }

            return r


async def user_by_id(i: int):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT id,name,display,authlvl,deleted FROM users WHERE id = ?", (i,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            r = {
                "id": row[0],
                "name": row[1],
                "display": row[2],
                "auth": row[3],
                "authstr": AuthLevels(row[3]).name,
                "deleted": bool(row[4]),
            }

            return r


async def tokenrevoke(token):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET token = ? WHERE token = ?", (None, token))
        await db.commit()


async def set_food(year, week, day, value):
    if not (1 <= day <= 7):
        raise ValueError("Invalid weekday index")

    col = weekdays[day - 1]

    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute(
            f"UPDATE weeks SET {col} = ? WHERE week = ? AND year = ?",
            (value, week, year),
        )
        await db.commit()

        if cursor.rowcount == 0:
            values = [""] * len(weekdays)
            values[day - 1] = value
            await db.execute(
                f"INSERT INTO weeks (year, week, {','.join(weekdays)}) VALUES (?, ?, {','.join(['?'] * len(weekdays))})",
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


async def delete_account(id):
    if id == 0:
        raise Exception("The Admin Account is protected!")
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE users SET (token,name,pass,display,authlvl,deleted) = (?,?,?,?,?,?) WHERE id = ?",
            ("", f"deleted_user{id}", "deletedaccount", "Deleted User", -1, 1, id),
        )
        await db.commit()


async def edit_permission(id, perm):
    if id == 0:
        raise Exception("The Admin Account is protected!")
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET authlvl = ? WHERE id = ?", (perm, id))
        await db.commit()


async def change_password(id, old, new):
    # the admin account is not protected against password changing.
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT pass FROM users WHERE id = ?", (id,)) as cursor:
            current = await cursor.fetchone()

        if not current or not verify_password(old, current[0]):
            raise Exception("Incorrect current password.")
        await db.execute(
            "UPDATE users SET pass = ? WHERE id = ?", (hash_password(new), id)
        )
        await db.commit()


async def getcomments(year, week, weekday):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT value, id, author FROM comments WHERE year = ? AND week = ? AND day = ?",
            (year, week, weekday),
        ) as cursor:
            selection = await cursor.fetchall()

        r = []
        for row in selection:
            r.append(
                {
                    "name": (await user_by_id(row[2]))["display"],
                    "comment": row[0],
                    "id": row[1],
                    "author": await get_author_by_comment_id(row[1]),
                }
            )
        return r


async def addcomment(year, week, weekday, value, authorid):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "INSERT INTO comments ( year, week, day, author, value, id ) VALUES ( ?, ?, ?, ?, ?, ? )",
            (year, week, weekday, authorid, value, await numcomments()),
        )
        await db.commit()


async def numcomments():
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM comments") as cursor:
            return len(list(await cursor.fetchall()))


async def changedisplay(id, new):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET display = ? WHERE id = ?", (new, id))
        await db.commit()


async def editlogin(id, new):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE name = ? AND id != ?", (new, id)
        ) as cursor:
            exists = await cursor.fetchone()

        if exists:
            raise Exception("Username already taken")

        await db.execute("UPDATE users SET name = ? WHERE id = ?", (new, id))
        await db.commit()


async def get_author_by_comment_id(id: int):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT author FROM comments WHERE id = ?", (id,)
        ) as cursor:
            id = (await cursor.fetchone())[0]
            info = await user_by_id(id)
            return f"{info['name']}#{id}"


async def delcomment(id, fr=False):
    async with aiosqlite.connect("database.db") as db:
        if not fr:
            await db.execute(
                "UPDATE comments SET value = ? WHERE id = ?",
                (
                    "<Deleted>",
                    id,
                ),
            )
        else:
            await db.execute("DELETE FROM comments WHERE id = ?", (id,))
        await db.commit()


async def getallcomments():
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT value, id, author,year,week,day FROM comments",
        ) as cursor:
            selection = await cursor.fetchall()

        r = {}
        for row in selection:
            r[
                str(
                    datetime.datetime.fromisocalendar(
                        row[3], row[4], row[5] + 1
                    ).strftime("%a %b %d %Y ")
                )
                + str(row[1])
            ] = {
                "name": (await user_by_id(row[2]))["display"],
                "comment": row[0],
                "id": row[1],
                "author": f"{(await user_by_id(row[2]))['name']}#{row[2]}",
                "date": [
                    datetime.datetime.fromisocalendar(row[3], row[4], row[5] + 1),
                    row[3],
                    row[4],
                    row[5],
                ],
            }
        return r


async def comment_by_id(id: int):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute(
            "SELECT value, id, author FROM comments WHERE id = ?",
            (id,),
        ) as cursor:
            row = await cursor.fetchone()

            return {
                "name": (await user_by_id(row[2]))["display"],
                "comment": row[0],
                "id": row[1],
                "author": await get_author_by_comment_id(row[1]),
            }


def init_app():
    asyncio.run(create_schema())


if __name__ == "__main__":
    init_app()
