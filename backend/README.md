# Backend

FastAPI service for the AI Stock Intelligence Platform.

## Commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

## Environment

Copy `.env.example` to `.env` and update values for your local machine.
