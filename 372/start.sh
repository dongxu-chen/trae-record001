#!/bin/bash
echo "Starting Image Segmentation Annotation Tool..."
echo ""

echo "[1/2] Starting FastAPI backend server..."
cd server && python main.py &
BACKEND_PID=$!

sleep 3

echo ""
echo "[2/2] Starting React dev server..."
cd ../client && npm run dev &
FRONTEND_PID=$!

echo ""
echo "Both servers started!"
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
