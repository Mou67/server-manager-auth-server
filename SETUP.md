# Server Manager OAuth Server - Setup Guide

## 🎯 Schnellstart

### Schritt 1: Discord App erstellen

1. Gehe zu: https://discord.com/developers/applications
2. Klick auf "New Application"
3. Name: "Server Manager"
4. Gehe zu "OAuth2" → "General"
5. Kopiere: **Client ID** und **Client Secret**
6. Gehe zu "OAuth2" → "Redirects"
7. Füge Redirect URI ein: `http://localhost:5001/auth/discord/callback`

### Schritt 2: Lokal Setup

```bash
# Repository klonen
git clone https://github.com/Mou67/server-manager-auth-server.git
cd server-manager-auth-server

# .env File erstellen
cp .env.example .env

# In .env Datei eintragen:
DISCORD_CLIENT_ID=deine_id_hier
DISCORD_CLIENT_SECRET=dein_secret_hier
DISCORD_BOT_TOKEN=dein_bot_token_hier
SECRET_KEY=generier_einen_zufallsstring
JWT_SECRET=generier_einen_zweiten_zufallsstring
```

### Schritt 3: Dependencies installieren

```bash
pip install -r requirements.txt
```

### Schritt 4: Testen

```bash
python app.py
```

Öffne: http://localhost:5001

Du solltest sehen:
```json
{
  "name": "Server Manager OAuth Server",
  "version": "1.0.0",
  "endpoints": { ... }
}
```

## 🚀 Auf Vercel deployen

### Schritt 1: GitHub Repository

```bash
git init
git add .
git commit -m "Initial: OAuth Server"
git branch -M main
git remote add origin https://github.com/Mou67/server-manager-auth-server.git
git push -u origin main
```

### Schritt 2: Vercel Setup

1. Gehe zu: https://vercel.com
2. Klick auf "New Project"
3. Wähle dein GitHub Repo
4. Klick "Deploy"

### Schritt 3: Environment Variables bei Vercel

1. Gehe zu Project Settings → Environment Variables
2. Füge folgende hinzu:

```
DISCORD_CLIENT_ID=deine_id
DISCORD_CLIENT_SECRET=dein_secret
DISCORD_BOT_TOKEN=dein_token
SECRET_KEY=zufallsstring_1
JWT_SECRET=zufallsstring_2
ADMIN_TOKEN=admin_123_ändern
```

3. Klick "Deploy"

### Schritt 4: Discord App aktualisieren

In Discord Developer Portal:
1. Gehe zu OAuth2 → Redirects
2. Änder Redirect URI zu: `https://your-vercel-url.vercel.app/auth/discord/callback`
   (Ersetze `your-vercel-url` mit deiner echten URL)

## 📝 Logging Struktur

Nach dem ersten Login findest du diese Dateien:

```
logs/
├── auth.log      # Login/Logout Events
├── actions.log   # Alle Benutzer-Aktionen
└── errors.log    # Fehler & Probleme

data/
└── users.json    # Alle registrierten Benutzer
```

## 🔌 Integration mit lokaler App

Deine lokale `app.py` sollte diese URL nutzen:

```python
OAUTH_SERVER = "https://your-vercel-url.vercel.app"  # Nach Deploy

# Discord Login zur OAuth Server leiten
@app.route('/auth/discord/login-redirect')
def discord_login_redirect():
    redirect_uri = "http://localhost:5000"  # Oder deine lokale URL
    return redirect(f"{OAUTH_SERVER}/auth/discord/login?redirect_uri={redirect_uri}")
```

## 🎯 Workflow

```
1. Benutzer: Klick "Mit Discord anmelden"
   ↓
2. Lokal App: Redirect zu OAuth Server
   ↓
3. OAuth Server: Discord OAuth Flow
   ↓
4. Discord: User gibt Permission
   ↓
5. OAuth Server: Generiert JWT Token
   ↓
6. Redirect zurück zu lokale App mit Token
   ↓
7. Lokal App: Speichert Token in Session
   ↓
8. Alle Aktionen werden zu OAuth Server geloggt
```

## 🔐 Admin Panel (lokal testen)

```bash
# Auth Logs anschauen
curl "http://localhost:5001/api/logs?admin_token=admin123&type=auth&limit=50"

# Actions Logs anschauen
curl "http://localhost:5001/api/logs?admin_token=admin123&type=actions&limit=50"

# Error Logs anschauen
curl "http://localhost:5001/api/logs?admin_token=admin123&type=errors&limit=50"

# Alle Benutzer
curl "http://localhost:5001/api/users?admin_token=admin123"
```

## ❓ Häufige Probleme

### 1. "OAUTHLIB_INSECURE_TRANSPORT" Error
**Lösung**: Das ist normal lokal. In Production ist HTTPS required.

### 2. "Redirect URI mismatch"
**Lösung**: Stelle sicher, dass die URI in Discord App genau mit der Route übereinstimmt.

### 3. Token ist ungültig
**Lösung**: Tokens laufen nach 7 Tagen ab. Benutzer muss sich neu anmelden.

### 4. Logs sind leer
**Lösung**: Server muss mit `python app.py` gestartet werden. Vercel logs sind unter Project → Logs.

## 📞 Testing Endpoints

```bash
# Health Check
curl http://localhost:5001/health

# Info
curl http://localhost:5001/

# Discord Login starten
curl -L http://localhost:5001/auth/discord/login

# Token validieren
curl -X POST http://localhost:5001/api/validate-token \
  -H "Content-Type: application/json" \
  -d '{"token":"your_jwt_token_here"}'

# Aktion loggen
curl -X POST http://localhost:5001/api/log-action \
  -H "Content-Type: application/json" \
  -d '{
    "token":"your_jwt_token_here",
    "action_type":"TEST_ACTION",
    "action_details":{"test":"value"}
  }'
```

## ✅ Deployment Checklist

- [ ] Discord App erstellt
- [ ] Client ID & Secret kopiert
- [ ] .env Datei konfiguriert
- [ ] Lokal getestet (python app.py)
- [ ] GitHub Repo erstellt
- [ ] Zu Vercel deployed
- [ ] Environment Variables bei Vercel gesetzt
- [ ] Vercel URL notiert
- [ ] Discord Redirect URI aktualisiert
- [ ] Production Redirect URI in Discord App gesetzt

## 🎉 Fertig!

Dein OAuth Server ist einsatzbereit! 🚀

**Nächster Schritt**: Deine lokale `app.py` mit dem OAuth Server verbinden.
