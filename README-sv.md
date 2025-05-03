# 🍽️ Skolmaten - Planering av skolmat

En minimal asynkron webbapp för hantering av veckovisa matmenyer (skolmaten) med användarautentisering och rollbaserade behörigheter. Byggd med [Flask](https://flask.palletsprojects.com/), [aiosqlite](https://github.com/omnilib/aiosqlite) och [python-jose](https://github.com/mpdavis/python-jose).

---

## ⚙️ Funktioner

- 🔐 JWT-baserat inloggningssystem med roller
- 🗓️ Veckobaserad matplanering
- 🧑‍💼 Rollbaserad administrationspanel
- 🌐 Asynkron med enkla HTML-formulär
- 🍞 Inbyggd SQLite-databas

---

## 🚀 Kom igång

### 1. Klona projektet

```bash
git clone https://github.com/spelis/skolmaten.git
# eller git@github.com:spelis/skolmaten.git
cd matsedel
```

### 2. Installera beroendepaket

```
pip install -r requirements.txt
```

### 3. Kör appen

```
python db.py # initialisera databasen
flask run # kör webbappen
```

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
