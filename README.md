# Innovasoft Proxy Gateway

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![HTTPX](https://img.shields.io/badge/HTTPX-async-2A6DB2?style=for-the-badge&logo=python&logoColor=white)](https://www.python-httpx.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Motor](https://img.shields.io/badge/Motor-async-13AA52?style=for-the-badge&logo=mongodb&logoColor=white)](https://motor.readthedocs.io/)
[![Poetry](https://img.shields.io/badge/Poetry-1.8%2B-60A5FA?style=for-the-badge&logo=poetry&logoColor=white)](https://python-poetry.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Pytest](https://img.shields.io/badge/Pytest-43%20passing-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Black](https://img.shields.io/badge/Code%20Style-Black-000000?style=for-the-badge)](https://black.readthedocs.io/)
[![Pylint](https://img.shields.io/badge/Pylint-10.00%2F10-A5B4FC?style=for-the-badge)](https://pylint.readthedocs.io/)

Technical Test for API Gateway/Proxy built with **FastAPI** that sits between the existing React frontend and the **Innovasoft S.A. API**.

```
React Frontend  →  FastAPI Proxy Gateway  →  https://pruebareactjs.test-class.com/Api/
                                          ↘  Local MongoDB (sessions, operations log)
```

The frontend only needs to **change its base URL** (from `https://pruebareactjs.test-class.com/Api/` to, for example, `http://localhost:8000/`). Routes and contracts are preserved 1:1.

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

## Exposed endpoints

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
- `InnovasoftClient` (URL building, bearer forwarding, timeout/network error → 504/502).
- `SessionService` (insert/upsert, idempotent deletion).
- `OperationLogService` (CREATE/UPDATE/DELETE logging; silent failure on insert errors).
- Integration tests with `respx`: successful login persists session, failed login does not, logout deletes it, invalid registration returns 422 without hitting upstream, list/CRUD forward the bearer token, upstream errors map to 502/504.

## Code quality

```bash
poetry run black .
poetry run isort .
poetry run flake8
poetry run pylint src
```
