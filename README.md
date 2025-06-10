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
cd skolmaten
```

### 2. Install Dependencies

```
pip install -r requirements.txt
```

### 3-1. Run the app 

```
gunicorn -w 4 -b 0.0.0.0:8000 'skolmaten:create_app()'
```

### 3-2. Run the app through Docker

```
touch database.db # create empty database
docker build -t skolmaten . # build docker container
docker run -d -p 8000:8000 -v ./database.db:/app/database.db skolmaten # run container and mount the database
```

### 3-3. Run the app in developer mode

```
flask --app skolmaten run --debug
```

### 4. Open in your browser

Open `localhost:8000` if you started with gunicorn or Docker. Otherwise you open `localhost:5000`


## 🧪 Default Admin Account

After running the program, the following account is created:

* Username: `adminacc`

* Password: `adminpassword`

Use it to invite/register other users.
It is also recommended you change the password. It can be changed by logging in and changing the password from the rightmost or center panel in the week view.

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
