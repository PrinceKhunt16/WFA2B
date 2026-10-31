# Wind Analytics Backend

This folder is the complete FastAPI project. It reads Elexon BMRS FUELHH and WINDFOR data, selects the latest forecast revision available at the configured day-ahead cutoff, matches forecast intervals with actual generation, and calculates accuracy metrics.

## Backend flow

1. `app/clients/elexon_client.py` asynchronously calls the official Elexon API with `httpx`, retries bounded transient failures, and caches responses briefly.
2. `app/services/data_service.py` fetches the requested delivery data and coordinates selection.
3. `app/services/forecast_selection.py` converts timestamps to UTC, applies the Europe/London cutoff policy, and selects the latest eligible WINDFOR publication per delivery interval.
4. `app/services/accuracy_service.py` normalizes half-hourly FUELHH actuals to the hourly WINDFOR granularity, matches records, and calculates MAE, RMSE, and bias.
5. `app/api/routes/` exposes typed FastAPI responses for the dashboard.

The default cutoff is `previous_day_11:00_europe_london`. Missing values are excluded from metrics, never replaced with zero. Elexon does not document exhaustive historical WINDFOR revision pagination, so responses report coverage limitations.

## Start locally

Run these commands from this `backend/` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`. Stop the server with `Ctrl+C` and leave the environment with `deactivate`.

## Validate

```bash
python -m compileall -q app tests
python -m pytest -q
python -m ruff check app tests
curl -fsS http://127.0.0.1:8000/health
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

For background mode and shutdown:

```bash
docker compose up --build -d
docker compose logs -f backend
docker compose down
```

## API routes

```text
GET /health
GET /api/v1/forecasts?date=YYYY-MM-DD
GET /api/v1/actuals?date=YYYY-MM-DD
GET /api/v1/comparison?date=YYYY-MM-DD
GET /api/v1/accuracy?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
GET /api/v1/summary
```

## Structure

```text
backend/
|-- app/main.py
|-- app/api/routes/
|-- app/clients/elexon_client.py
|-- app/core/
|-- app/schemas/
|-- app/services/
|-- app/utils/
|-- tests/
|-- requirements.txt
|-- pyproject.toml
|-- Dockerfile
|-- docker-compose.yml
|-- .env.example
`-- README.md
```

## Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend docs: `http://127.0.0.1:8000/docs`

Validate the backend from `backend/`:

```bash
python -m pytest -q
python -m ruff check app tests
```

## Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend dashboard: `http://localhost:3000`