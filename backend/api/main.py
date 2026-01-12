"""
FastAPI Main Application
Entry point for REST API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Uzbek Receipt Parser API",
    description="High-load financial transaction parsing system for Uzbek banking receipts",
    version="1.0.0"
)

# CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5180",
        "http://localhost:5179",
        "http://localhost:5178",
        "http://localhost:5177",
        "http://localhost:5176",
        "http://localhost:5175",
        "http://localhost:5174",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Starting Uzbek Receipt Parser API...")
    
    # Initialize database
    from database.connection import init_db
    init_db()
    print("✅ Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Shutting down API...")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Uzbek Receipt Parser",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    from database.connection import engine
    from sqlalchemy import text

    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "version": "1.0.0"
    }


# Import and register routes
from api.routes import transactions, analytics, reference, automation, userbot, auth

app.include_router(auth.router, tags=["Authentication"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(reference.router, prefix="/api/reference", tags=["Reference"])
app.include_router(automation.router, tags=["Automation"])
app.include_router(userbot.router, tags=["Userbot"])
