from fastapi import FastAPI
import os

app = FastAPI(title="Gym Equipment Directory")

@app.get("/health")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV", "dev")}
