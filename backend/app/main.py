from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from .routers import names, users, sales, work, transactions, auth
from .database import engine, Base
from .bootstrap import bootstrap_admin

# Create tables on startup (for simple verified stability as requested)
# In production, use Alembic for migrations
Base.metadata.create_all(bind=engine)

# create_all doesn't add columns to existing tables - add password_hash if missing
if "password_hash" not in {c["name"] for c in inspect(engine).get_columns("users")}:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))

bootstrap_admin()

app = FastAPI(
    title="Brick Bhatta Management System API",
    description="Backend for Brick Bhatta Management System Flutter App",
    version="1.0.0",
)

# CORS Configuration
origins = ["*"] # Allow all for development. Restrict in production.

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(names.router)
app.include_router(users.router)
app.include_router(sales.router)
app.include_router(work.router)
app.include_router(transactions.router)
app.include_router(auth.router)

@app.get("/health")
def read_health():
    return {"status": "ok", "message": "Service is running"}

@app.get("/")
def read_root():
    return {"message": "Welcome to Brick Bhatta Management System API"}
