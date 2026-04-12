import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import yaml
import os
import sys
import torch

app = FastAPI(title="Satellite Telemetry Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

class InferRequest(BaseModel):
    data: list
    channel: str = "T-1"

class TrainRequest(BaseModel):
    dataset: str = "SMAP"
    epochs: int = 5

@app.get("/")
def root():
    return {"message": "Satellite Telemetry Backend running"}

@app.get("/health")
def health():
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
    return {
        "status": "healthy",
        "cuda": cuda_available,
        "device": device_name
    }

@app.post("/infer")
def infer(req: InferRequest):
    try:
        from infer import run_inference
        data = np.array(req.data)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        result = run_inference(data)
        result["channel"] = req.channel
        return result
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Model not found. Please train the model first via /train"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train")
def train(req: TrainRequest):
    try:
        from train import train as run_train
        run_train()
        return {"status": "training started", "dataset": req.dataset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/channels")
def get_channels():
    config = load_config()
    data_dir = os.path.join(config["paths"]["data_dir"], "train")
    if not os.path.exists(data_dir):
        return {"channels": [f"T-{i}" for i in range(1, 56)]}
    channels = [
        f.replace(".npy", "")
        for f in os.listdir(data_dir)
        if f.endswith(".npy")
    ]
    return {"channels": sorted(channels)}

if __name__ == "__main__":
    config = load_config()
    uvicorn.run(
        app,
        host=config["server"]["host"],
        port=config["server"]["port"]
    )