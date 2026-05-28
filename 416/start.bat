@echo off
echo Starting Knowledge Base Q&A System...
echo.

if not exist ".env" (
    echo Warning: .env file not found. Copying .env.example...
    copy .env.example .env
    echo.
    echo Please edit .env file to configure your API keys before running again.
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
echo.

echo Starting FastAPI server on http://localhost:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
