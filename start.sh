
#!/bin/bash
# Railway deployment start script for both backend and frontend

# Start backend
cd backend
source venv/bin/activate
nohup python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 &
cd ..

# Start frontend
cd frontend
npm install --omit=dev
npm run build
npx serve -s dist -l 8080
