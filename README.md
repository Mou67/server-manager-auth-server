# Server Manager OAuth Server

Zentraler OAuth2-Server für den Server Manager. Handles Discord-Authentifizierung, Token-Generierung und umfassendes Logging.

## 🎯 Features

- ✅ Discord OAuth2 Integration
- ✅ JWT Token Generation & Validation
- ✅ Umfassendes Logging System (Auth, Actions, Errors)
- ✅ Benutzerverwaltung
- ✅ API Endpoints für lokale App
- ✅ Vercel Ready (kostenlos)

## 📋 Setup

### 1. Discord App erstellen

1. Gehe zu: https://discord.com/developers/applications
2. Neue Anwendung erstellen
3. In "OAuth2" → "General" die Credentials kopieren
4. Redirect URI hinzufügen:
   - Lokal: `http://localhost:5001/auth/discord/callback`
   - Production: `https://your-vercel-url.vercel.app/auth/discord/callback`

### 2. Environment Setup (lokal)

```bash
# .env erstellen
cp .env.example .env

# Discord Credentials einfügen:
DISCORD_CLIENT_ID=your_id
DISCORD_CLIENT_SECRET=your_secret
DISCORD_BOT_TOKEN=your_token
SECRET_KEY=generate_random_string
JWT_SECRET=generate_random_string
```

### 3. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 4. Lokal testen

```bash
python app.py
```

Server läuft auf: `http://localhost:5001`

## 🚀 Vercel Deployment

### 1. Repository auf GitHub pushen

```bash
git init
git add .
git commit -m "Initial commit: OAuth Server"
git remote add origin https://github.com/Mou67/server-manager-auth-server.git
git push -u origin main
```

### 2. Auf Vercel deployen

1. Gehe zu: https://vercel.com/new
2. GitHub Repo verbinden
3. Environment Variables setzen:
   - `DISCORD_CLIENT_ID`
   - `DISCORD_CLIENT_SECRET`
   - `DISCORD_BOT_TOKEN`
   - `SECRET_KEY` (generiert)
   - `JWT_SECRET` (generiert)
   - `ADMIN_TOKEN` (generiert)

4. Deploy!

### 3. Discord App aktualisieren

In Discord Developer Portal:
- Redirect URI aktualisieren: `https://your-vercel-url.vercel.app/auth/discord/callback`

## 📡 API Endpoints

### Authentication

```
GET /auth/discord/login
→ Startet Discord OAuth

GET /auth/discord/callback
→ Discord Callback Handler

POST /auth/logout
Body: { "token": "jwt_token" }
→ Logout User
```

### Validation & Logging

```
POST /api/validate-token
Body: { "token": "jwt_token" }
→ Validiert JWT Token

POST /api/log-action
Body: {
  "token": "jwt_token",
  "action_type": "action_name",
  "action_details": { ... }
}
→ Loggt User-Aktion
```

### Admin

```
GET /api/users?admin_token=admin123
→ Alle Benutzer

GET /api/logs?admin_token=admin123&type=auth&limit=100
→ Logs (types: auth, actions, errors)
```

## 📊 Logging System

### Auth Log (`logs/auth.log`)
```json
{
  "timestamp": "2025-11-02T12:00:00",
  "event_type": "LOGIN_SUCCESS",
  "user_id": 123456789,
  "username": "mou67",
  "details": { "method": "discord" }
}
```

### Actions Log (`logs/actions.log`)
```json
{
  "timestamp": "2025-11-02T12:00:00",
  "action_type": "SERVER_START",
  "user_id": 123456789,
  "username": "mou67",
  "action_details": { "server_id": 1 },
  "ip_address": "192.168.1.1"
}
```

### Errors Log (`logs/errors.log`)
```json
{
  "timestamp": "2025-11-02T12:00:00",
  "error_type": "JWT_EXPIRED",
  "error_message": "Token expired",
  "user_id": 123456789
}
```

## 🔌 Integration mit lokaler App

In deiner `app.py`:

```python
# Login mit OAuth Server
OAUTH_SERVER = "https://your-vercel-url.vercel.app"
OAUTH_REDIRECT_URI = "http://localhost:5000"

# Discord Login zur OAuth Server leiten
@app.route('/login/discord')
def discord_login():
    return redirect(f"{OAUTH_SERVER}/auth/discord/login?redirect_uri={OAUTH_REDIRECT_URI}")

# Token von OAuth Server validieren
@app.route('/auth/callback')
def auth_callback():
    token = request.args.get('token')
    response = requests.post(f"{OAUTH_SERVER}/api/validate-token", json={"token": token})
    # Token in Session speichern
    session['token'] = token

# Aktionen loggen
def log_user_action(action_type, details):
    requests.post(
        f"{OAUTH_SERVER}/api/log-action",
        json={
            "token": session.get('token'),
            "action_type": action_type,
            "action_details": details
        }
    )
```

## 📁 Dateistruktur

```
server-manager-auth-server/
├── app.py                    # Hauptanwendung
├── requirements.txt          # Dependencies
├── vercel.json              # Vercel Config
├── .env.example             # Environment Template
├── logs/
│   ├── auth.log             # Authentifizierungs-Events
│   ├── actions.log          # Benutzer-Aktionen
│   └── errors.log           # Fehler
├── data/
│   └── users.json           # Benutzerdatenbank
└── README.md                # Diese Datei
```

## 🔒 Security Best Practices

- ✅ JWT Tokens mit Ablaufdatum (7 Tage)
- ✅ Admin-Token für sensitive Endpoints
- ✅ CORS Konfiguration
- ✅ Error Logging ohne sensitive Daten
- ✅ IP Tracking für Aktionen

## 🛠️ Troubleshooting

### "Could not build url for endpoint"
→ Stelle sicher, dass die Flask App korrekt startet

### "Invalid token"
→ Token ist abgelaufen (7 Tage) oder ungültig

### Discord Redirect nicht konfiguriert
→ Aktualisiere die Redirect URI in Discord Developer Portal

## 📞 Support

Bei Fragen oder Problemen:
1. Check logs in `logs/errors.log`
2. Vercel Logs: `vercel logs your-project-name`
3. GitHub Issues

---

Made with ❤️ for Server Manager
