import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import yaml
import os
import sys
import torch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Satellite Telemetry Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def validate_env_vars():
    """Validate that required environment variables are set."""
    optional_vars = ['ANTHROPIC_API_KEY', 'BACKEND_URL']
    missing = []
    for var in optional_vars:
        if not os.getenv(var):
            print(f"WARNING: Optional environment variable {var} not set")

def load_config():
    """Load configuration from config.yaml with error handling."""
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found at {config_path}. "
            f"Please ensure config.yaml exists in the application directory."
        )
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            if not config:
                raise ValueError("Config file is empty or invalid YAML")
            return config
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {str(e)}")
    except Exception as e:
        raise Exception(f"Error loading config: {str(e)}")

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
        print(f"Received inference request for channel {req.channel} with shape {data.shape}")
        result = run_inference(data)
        result["channel"] = req.channel
        return result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {str(e)}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train")
def train(req: TrainRequest):
    try:
        from train import train as run_train
        # Pass dataset and epochs parameters to training function
        run_train(dataset=req.dataset, epochs=req.epochs)
        return {"status": "training started", "dataset": req.dataset, "epochs": req.epochs}
    except Exception as e:
        import traceback
        traceback.print_exc()
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
    try:
        # Validate environment variables
        validate_env_vars()
        
        # Load configuration
        config = load_config()
        
        # Extract server configuration
        server_config = config.get("server", {})
        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8001)
        
        print(f"Starting Satellite Telemetry Backend on {host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port
        )
    except Exception as e:
        print(f"FATAL ERROR: Failed to start application: {str(e)}")
        sys.exit(1)