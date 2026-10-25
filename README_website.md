# Remote Access to your home systems

This repository contains a simple nginx setup
The NGINX config is the most important part.

It contains 2 types of config

1. initial website which contains the links to the different internal systems
2. reverse-proxy config for the internal systems

It assumes you have a working Apache Guacamole system.
It can be another system or locally via docker

A root-level `docker-compose.yml` builds and runs service.

## Prerequisites

- Docker installed
- Docker Compose v2 (bundled with recent Docker installations)
- Terminal access

## Project Structure

- `certs`: Holds all the necessary certificate files, at least server.crt and server.key for the website.
- `config`: Holds the nginx config file
- `backend`: Flask API that handles the dashboard links and settings (CRUD) and persists them to `data/links.json`.
- `data`: Holds `links.json` (git-ignored, created automatically on first save) and `links.json.example` as a template.
- `html`: Holds the index.html and error file 403 access denied and 404 not found.
- `docker-compose.yml`: builds the service

## Quick Start

### 1. Create certificates

First time setup:

1. copy config sample to nginx.conf

```bash
cp config/default.conf-sample config/default.conf
```

**To create the cert structure, see the README.md in certs dir.**

### 2. Add initial links (optional)

The dashboard links are stored in `data/links.json`.  
The first url is the standard link to the remote access /guacamole  

To start with example tiles, copy the example file:

```bash
cp data/links.json.example data/links.json
```

Each link has `label`, `url` (`http://`, `https://` or a `/path`), `description`, `category` (`remote` or `local`), `newTab` (`true`/`false`) and a unique `id`.
Without this step the dashboard starts empty; tiles can also be added in the browser via the pen icon (edit mode).

### 3. Start Services

Build and start both services:

```bash
docker compose up -d
```

- **Website**: <http://localhost> | <https://localhost>

### 4. Stop Services

```bash
docker compose down
```
