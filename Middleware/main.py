from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Satellite Telemetry Middleware", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import predict, alerts, channels

app.include_router(predict.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(channels.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Middleware running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)