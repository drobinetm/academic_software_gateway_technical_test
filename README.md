# Academic software  (Proxy Gateway) technical test 

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![HTTPX](https://img.shields.io/badge/HTTPX-async-2A6DB2?style=for-the-badge&logo=python&logoColor=white)](https://www.python-httpx.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Motor](https://img.shields.io/badge/Motor-async-13AA52?style=for-the-badge&logo=mongodb&logoColor=white)](https://motor.readthedocs.io/)
[![Poetry](https://img.shields.io/badge/Poetry-1.8%2B-60A5FA?style=for-the-badge&logo=poetry&logoColor=white)](https://python-poetry.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Black](https://img.shields.io/badge/Code%20Style-Black-000000?style=for-the-badge)](https://black.readthedocs.io/)
[![Pylint](https://img.shields.io/badge/Pylint-10.00%2F10-A5B4FC?style=for-the-badge)](https://pylint.readthedocs.io/)

## What is it?

**Innovasoft Proxy Gateway** is an API Gateway built with **FastAPI** that acts as a transparent intermediary between an existing React frontend and the official **Innovasoft S.A. API**. It intercepts every request from the frontend, forwards it to the upstream API, and returns the response — while adding session persistence, CRUD audit logging, input validation and centralised error handling on top.

```
React Frontend  →  FastAPI Proxy Gateway  →  https://pruebareactjs.test-class.com/Api/
                                          ↘  Local MongoDB (sessions, operations log)
```

## What problem does it solve?

The frontend was directly coupled to the Innovasoft API, which meant:

- **No control layer** between the client and the upstream service — any upstream change or downtime hit the frontend immediately.
- **No session management** — tokens were not tracked locally, making it impossible to audit active sessions or enforce logout server-side.
- **No audit trail** — create, update and delete operations over clients were not recorded anywhere.
- **No input validation gateway** — invalid or malformed requests reached the upstream without being intercepted.

This gateway solves all of the above. The frontend only needs to **change its base URL** (from `https://pruebareactjs.test-class.com/Api/` to, for example, `http://localhost:8000/`). Routes and contracts are preserved 1:1 — no other frontend changes required.

## Requirements

- Python **3.10+**
- [Poetry](https://python-poetry.org/) ≥ 1.8
- Docker + Docker Compose (for MongoDB)

## Installation

```bash
git clone <repo>
cd academic_software_gateway_technical_test
poetry install
cp .env.example .env
```

Edit `.env` if you need to tweak URLs, ports or `CORS_ORIGINS`.

## Start MongoDB

```bash
docker compose up -d mongodb
```

This exposes MongoDB on `localhost:27017` and persists data to the `mongodb_data` volume.

## Database admin UI (development)

[Mongo Express](https://github.com/mongo-express/mongo-express) is included in `docker-compose.yml` as a lightweight web UI to browse the MongoDB collections (`sesiones`, `operaciones`, `request_logs`) during local development.

```bash
docker compose up -d mongo-express
```

Open <http://localhost:8081> in the browser:

- **Username:** `admin`
- **Password:** `admin`

> Mongo Express is intended for local development only. Do not expose port `8081` in any non-local environment.

## Run the gateway

```bash
poetry run uvicorn src.main:app --reload --port 8000
```

- Swagger UI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

## Point the frontend at the gateway

In the React frontend, change the HTTP client **base URL**:

```diff
- const BASE_URL = "https://pruebareactjs.test-class.com/Api/";
+ const BASE_URL = "http://localhost:8000/";
```

No other changes are required: the routes (`/api/Authenticate/login`, `/api/Cliente/Listado`, etc.) are identical.

## Exposed endpoints with this API Gateway

| Method  | Path                                  | Description                                                |
| ------- | ------------------------------------- | ---------------------------------------------------------- |
| POST    | `/api/Authenticate/login`             | Login. On success, persists the session in MongoDB.        |
| POST    | `/api/Authenticate/register`          | User registration (email/password validation).             |
| POST    | `/api/Authenticate/logout`            | Logout. Removes the session matching the bearer token.     |
| POST    | `/api/Cliente/Listado`                | List clients (bearer token required).                      |
| GET     | `/api/Cliente/Obtener/{idCliente}`    | Get client detail.                                         |
| POST    | `/api/Cliente/Crear`                  | Create client. Logs `CREAR` in `operaciones`.              |
| POST    | `/api/Cliente/Actualizar`             | Update client. Logs `ACTUALIZAR`.                          |
| DELETE  | `/api/Cliente/Eliminar/{idCliente}`   | Delete client. Logs `ELIMINAR`.                            |
| GET     | `/api/Intereses/Listado`              | Interests catalog.                                         |
| GET     | `/health`                             | Gateway health check.                                      |

## Tests

```bash
poetry run pytest
poetry run pytest --cov=src --cov-report=term-missing
```

The suite covers:

- Schema validation (login, registration, client).
- `ProxyService` (URL building, bearer forwarding, header filtering, timeout/network error → 504/502).
- `SessionService` (insert/upsert, idempotent deletion).
- `OperationLogService` (CREATE/UPDATE/DELETE logging; silent failure on insert errors).
- `RequestLogService` + `HTTPRequestLogMiddleware` (every gateway request persisted in `request_logs`).
- `ROUTE_HOOKS` registry and the catch-all proxy: validation 422, passthrough GET, audit on CREATE/UPDATE/DELETE, query-param/header propagation.
- OpenAPI merging: live → cache → native fallback; logout injection; password regex reinforced.
- Integration tests with `respx`: successful login persists session, failed login does not, logout deletes it, invalid registration returns 422 without hitting upstream, list/CRUD forward the bearer token, upstream errors map to 502/504.

## Architecture notes

- **Single proxy entry point.** `src/api/routes/proxy.py` exposes one catch-all handler `@router.api_route("/api/{full_path:path}")` that forwards everything to Innovasoft via `ProxyService.forward(...)`. Routes that need extra behaviour (Pydantic validation or audit logging) declare it through the `ROUTE_HOOKS_EXACT` / `ROUTE_HOOKS_REGEX` table — no new `@router.<verb>` decorators required.
- **`auth.py` is the only domain-explicit router.** Login persists a session; logout is **terminal-local** (does NOT call upstream — Innovasoft has no logout endpoint, the PDF only requires deleting the local session document). Register goes through `ProxyService` like everything else.
- **Router order is mandatory** in `main.py`: `auth.router` BEFORE `proxy.router`, otherwise the catch-all swallows `/api/Authenticate/login`.
- **Inherited OpenAPI schema.** At startup the gateway tries to fetch the upstream `swagger/v1/swagger.json` live, falls back to `static/innovasoft_openapi_cache.json`, and finally to FastAPI's native schema. The merged spec rebrands the title, points `servers` at `/`, injects the local logout endpoint, and reinforces the password regex.
- **`request_logs` collection.** Every non-excluded HTTP request through the gateway is persisted as a document with `method`, `path`, `status`, `duration_ms`, `client_ip`, `user_agent`, `timestamp`, etc. Excluded paths: `/docs`, `/redoc`, `/openapi.json`, `/health`, `/favicon.ico`. TTL optional via `REQUEST_LOG_TTL_SECONDS`.
- **Upstream inconsistencies are preserved**, not normalised: `celular` / `telefonoCelular`, `interesFK` / `interesesId`, `resenaPersonal` / `resennaPersonal` reach the upstream as the frontend currently sends them.

### Refresh the upstream OpenAPI cache

If the upstream swagger changes, regenerate the embedded snapshot:

```bash
poetry run refresh-openapi
```

This writes `static/innovasoft_openapi_cache.json`, which is the offline fallback when the live fetch fails at startup.

## Code quality

```bash
poetry run black src
poetry run isort src
poetry run flake8 src
poetry run pylint src

# Or run all commands 
poetry run isort --atomic src && poetry run black --target-version=py311 src && poetry run pylint --rcfile=.pylintrc src
```
