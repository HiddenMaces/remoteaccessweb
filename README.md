# RemoteAccessWeb

A self-hosted remote access gateway. It combines a **SentinelOne-styled dashboard** (Nginx + Flask) with **Apache Guacamole** for clientless browser-based remote desktop access — all protected by mutual TLS (mTLS) so only clients with a valid certificate can connect.

---

## Architecture

```
Browser (with client cert)
        │
        ▼  HTTPS + mTLS (port 443)
┌───────────────────┐
│   ras-web (Nginx) │  ← TLS termination, mTLS enforcement, reverse proxy
└───────┬───────────┘
        │
        ├──/api/──────────────────► ras-api (Flask :5000)
        │                            Dashboard link CRUD, persists to links.json
        │
        └──/guacamole/────────────► guacamole (:8080)
                                     │
                                     ├── guacd  (protocol daemon)
                                     └── guacdb (MariaDB)
```

| Container | Image | Role |
|-----------|-------|------|
| `ras-web` | nginx:1.27-alpine | HTTPS frontend, mTLS, reverse proxy |
| `ras-api` | python:3.12-slim + Flask | Dashboard CRUD API |
| `guacamole` | guacamole/guacamole:1.5.5 | Web UI for remote sessions |
| `guacd` | guacamole/guacd:1.5.5 | Guacamole protocol daemon |
| `guacdb` | mariadb:10.11 | Guacamole database |

---

## Prerequisites

- Docker Engine with Compose v2 (`docker compose` — not `docker-compose`)
- `openssl` for generating certificates
- A DNS name or hostname for your server

---

## First-time setup

### 1. Set credentials

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder values with strong passwords:

```
DB_ROOT_PASSWORD=your_strong_root_password
DB_NAME=guacamole_db
DB_USER=guacamole_user
DB_PASSWORD=your_strong_user_password
```

> `.env` is git-ignored — never commit it.

---

### 2. Generate certificates

You need three files in `website/certs/`:

| File | Purpose |
|------|---------|
| `rootCA.crt` | Your private CA — used by Nginx to verify client certs |
| `<fqdn>.crt` | Server certificate for HTTPS |
| `<fqdn>.key` | Server private key |

Full instructions for creating a private Root CA, server certs, and per-user client certs are in **[README_certificates.md](README_certificates.md)**.

---

### 3. Configure Nginx

Copy the sample config and update it with your hostname and certificate filenames:

```bash
cp website/config/default.conf-sample website/config/default.conf
```

Edit `website/config/default.conf` — replace the `fqdn` placeholders and cert filenames to match your setup.

---

### 4. Initialise the Guacamole database

This only needs to run once. It starts the database container, loads the schema, then stops it.

```bash
bash init_guac_db.sh
```

> The script reads credentials from `guacamole/.env`. If you are running the guacamole sub-compose standalone, copy the example there too:
> ```bash
> cp guacamole/.env.example guacamole/.env
> ```

---

### 5. Start the full stack

```bash
docker compose up -d
```

Services are available at:

| URL | Service |
|-----|---------|
| `https://<fqdn>/` | Dashboard |
| `https://<fqdn>/guacamole/` | Guacamole remote access |

---

### 6. Change the Guacamole admin password

On first login use `guacadmin` / `guacadmin`, then immediately go to:

**Settings → Preferences → Change Password**

---

## Dashboard

The dashboard is a tile-based link launcher. Tiles are stored in `website/data/links.json` via a REST API — no file editing required.

### Initial data (optional)

`links.json` is git-ignored and created automatically on first save. To start with pre-defined tiles, copy the example:

```bash
cp website/data/links.json.example website/data/links.json
```

Each link has `label`, `url` (`http://`, `https://` or a `/path`), `description`, `category` (`remote` or `local`), `newTab` (`true`/`false`) and a unique `id`.

### Managing tiles

Click the **pen icon** (top right) to enter edit mode:

- **Add** — click the dashed *Add Tile* card that appears
- **Edit** — click the pencil button on any tile
- **Delete** — click the trash button on any tile, then confirm
- **Reorder** — drag tiles to the desired position

### Settings

Click the **gear icon** (top right) to update the page title and contact email shown in the footer.

---

## Stopping the stack

```bash
docker compose down
```

Add `-v` only if you also want to wipe database volumes.

---

## Directory structure

```
.
├── .env.example                  # Credential template — copy to .env
├── docker-compose.yaml           # Full stack (uses include, recommended)
├── docker-compose.yaml-all       # All-in-one alternative (no includes)
├── init_guac_db.sh               # One-shot database initialisation script
│
├── website/
│   ├── backend/                  # Flask CRUD API
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── certs/                    # TLS certs — git-ignored, create manually
│   ├── config/
│   │   ├── default.conf          # Active Nginx config (create from sample)
│   │   └── default.conf-sample   # Template with placeholders
│   ├── data/
│   │   ├── links.json            # Persisted dashboard links — git-ignored
│   │   └── links.json.example    # Example data — copy to links.json
│   ├── html/
│   │   ├── index.html            # Dashboard frontend
│   │   ├── 403error.html
│   │   └── 404error.html
│   └── docker-compose.yaml       # Website + API services
│
└── guacamole/
    ├── .env.example              # Credential template for standalone use
    ├── db-data/                  # MariaDB data volume — git-ignored
    ├── docker-compose.yaml       # Guacamole services
    └── initdb.sql                # Database schema + default admin user
```

---

## Security model

Access to the entire gateway is controlled by **Mutual TLS (mTLS)**:

- The server presents its certificate (standard HTTPS)
- The client **must** present a certificate signed by your private Root CA
- Nginx enforces this with `ssl_verify_client on` — no valid cert means a 403

This means both the dashboard and Guacamole are only reachable by clients you have explicitly issued a certificate to. Guacamole's port 8080 is **not** exposed on the host; it is only accessible internally through the Nginx proxy.

See **[README_certificates.md](README_certificates.md)** for the full guide on creating and issuing server and client certificates.

---

## Dashboard API reference

The Flask backend exposes a REST API under `/api/` (proxied by Nginx):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/links` | Fetch all links and settings |
| `POST` | `/api/links` | Create a link `{label, url, description}` |
| `PUT` | `/api/links/<id>` | Update a link |
| `DELETE` | `/api/links/<id>` | Delete a link |
| `POST` | `/api/links/reorder` | Save tile order `{ids: [...]}` |
| `GET` | `/api/settings` | Get page title and email |
| `PUT` | `/api/settings` | Update page title and email |
