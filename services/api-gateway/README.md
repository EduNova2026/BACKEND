# API Gateway

First FastAPI service for the EDU'NOVA backend.

## Local endpoints

- `GET /health`
- `GET /health/detailed`
- `GET /api/v1/gateway/status`

## Run from backend workspace

```bash
uv run uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```
