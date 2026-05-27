from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import health, orders

app = FastAPI(
    title="LPR Search AI Module",
    description="Сервис для интеллектуального поиска контактов ЛПР.",
    version="0.1.0"
)

# === CORS ДЛЯ ПРОДА ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://admin-lpr-navigator.ru",
        "https://www.admin-lpr-navigator.ru",
        "http://admin-lpr-navigator.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "LPR Search AI Service is running"}