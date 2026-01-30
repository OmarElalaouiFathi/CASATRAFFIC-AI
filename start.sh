
#!/bin/sh
# Railway deployment start script (backend only, sh compatible)

cd backend
. venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
