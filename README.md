> [!NOTE]
> En svensk översättning av denna README kan hittas med namnet `README-sv.md`

# 🍽️ Skolmaten - School food planning

A minimal async web app for managing weekly food menus (skolmaten) with user authentication and role-based permissions. Built with [Flask](https://flask.palletsprojects.com/), [aiosqlite](https://github.com/omnilib/aiosqlite), and [python-jose](https://github.com/mpdavis/python-jose).

---

## ⚙️ Features

- 🔐 JWT-based login system with roles
- 🗓️ Week-based food planning
- 🧑‍💼 Role-based management dashboard
- 🌐 Async-first with simple HTML forms
- 🍞 Built-in SQLite database

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/spelis/skolmaten.git
# or git@github.com:spelis/skolmaten.git
cd matsedel
```

### 2. Install Dependencies

```
pip install -r requirements.txt
```

### 3. Run the app

```
python db.py # initialize the database
flask run # run the web app
```

## 🧪 Default Admin Account

After running `db.py`, the following account is created:

* Username: `adminacc`

* Password: `adminpassword`

Use it to invite/register other users.
It is also recommended you change the password. It can be found in the `db.py` file in the `create_schema()` function.

## 🔒 Permissions

|Role      |Value|Can Edit Food|Can Manage Users|
|----------|-----|-------------|----------------|
|User      |0    |❌ |❌ |
|FoodEditor|1    |✅ |❌ |
|Moderator |2    |✅ |✅ |
|Admin     |3    |✅ |✅ |

## 🧠 Tech Stack
* Flask
* aiosqlite
* jose
