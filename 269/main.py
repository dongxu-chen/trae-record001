import uvicorn
from api.main import app

if __name__ == "__main__":
    print("=" * 60)
    print("  Music Recommendation System")
    print("=" * 60)
    print()
    print("Starting FastAPI server on http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print()
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
