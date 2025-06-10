# 🍽️ Skolmaten - Planering av skolmat

En minimal asynkron webbapp för hantering av veckovisa matmenyer (skolmaten) med användarautentisering och rollbaserade behörigheter. Byggd med [Flask](https://flask.palletsprojects.com/), [aiosqlite](https://github.com/omnilib/aiosqlite) och [python-jose](https://github.com/mpdavis/python-jose).

---

## ⚙️ Funktioner

- 🔐 JWT-baserat inloggningssystem med roller
- 🗓️ Veckobaserad matplanering
- 🧑‍💼 Rollbaserad administrationspanel
- 🌐 Async-först med enkla HTML-formulär
- 🍞 Inbyggd SQLite-databas

---

## 🚀 Kom igång

### 1. Klona projektet

```bash
git clone https://github.com/spelis/skolmaten.git
# eller git@github.com:spelis/skolmaten.git
cd skolmaten
```

### 2. Installera beroendepaket

```
pip install -r requirements.txt
```

### 3-1. Kör appen

```
gunicorn -w 4 -b 0.0.0.0:8000 'skolmaten:create_app()'
```

### 3-2. Kör appen via Docker

```
touch database.db # skapa en tom databas
docker build -t skolmaten . # bygg docker-container
docker run -d -p 8000:8000 -v ./database.db:/app/database.db skolmaten # kör container och montera databasen
```

### 3-3. Kör appen i utvecklingsläge

```
flask --app skolmaten run --debug
```

### 4. Öppna i webbläsare

Öppna `localhost:8000` om du startade med gunicorn eller Docker. Annars öppnar du `localhost:5000`

## 🧪 Standard administratörskonto

Efter att ha kört `db.py` skapas följande kontot:

* Användarnamn: `adminacc`

* Lösenord: `adminpassword`

Använd det för att bjuda in/registrera andra användare.
Det rekommenderas också att du ändrar lösenordet. Det kan du göra genom att logga in och ändra lösenordet från högersta panelen i veckoplanen.

## 🔒 Behörigheter

|Roll      |Värde|Kan redigera mat|Kan hantera användare|
|----------|-----|----------------|---------------------|
|User |0    |❌ |❌ |
|FoodEditor|1 |✅ |❌ |
|Moderator |2    |✅ |✅ |
|Admin     |3    |✅ |✅ |

## 🧠 Teknisk stack
* Flask
* aiosqlite
* jose
