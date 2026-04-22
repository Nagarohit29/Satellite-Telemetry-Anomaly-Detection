import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import yaml
import os
import sys
import torch
import csv
from functools import lru_cache
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


def _backend_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _smap_msl_root() -> str:
    return os.path.join(_backend_root(), "data", "SMAP_MSL")


@lru_cache(maxsize=1)
def _load_channel_metadata() -> dict:
    metadata = {}
    csv_path = os.path.join(_smap_msl_root(), "labeled_anomalies.csv")
    if not os.path.exists(csv_path):
        return metadata

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            channel = row.get("chan_id")
            spacecraft = row.get("spacecraft")
            if channel and spacecraft and channel not in metadata:
                metadata[channel] = spacecraft
    return metadata


@lru_cache(maxsize=64)
def _load_channel_series(channel: str) -> np.ndarray:
    channel = channel.strip()
    candidate_paths = [
        os.path.join(_smap_msl_root(), "test", f"{channel}.npy"),
        os.path.join(_smap_msl_root(), "train", f"{channel}.npy"),
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            data = np.load(path)
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            return data.astype(np.float32, copy=False)
    raise FileNotFoundError(f"No telemetry series found for channel {channel}")


def _list_available_channels(dataset: str) -> list[str]:
    metadata = _load_channel_metadata()
    if metadata:
        if dataset:
            channels = [channel for channel, spacecraft in metadata.items() if spacecraft == dataset]
            if channels:
                return sorted(channels)
        return sorted(metadata.keys())

    test_dir = os.path.join(_smap_msl_root(), "test")
    if os.path.exists(test_dir):
        return sorted(
            f.replace(".npy", "")
            for f in os.listdir(test_dir)
            if f.endswith(".npy")
        )
    return []


def _slice_replay_window(series: np.ndarray, offset: int, length: int) -> tuple[np.ndarray, int]:
    total_points = len(series)
    if total_points == 0:
        raise ValueError("Telemetry series is empty")

    length = max(20, min(length, total_points))
    start = offset % total_points
    end = start + length

    if end <= total_points:
        window = series[start:end]
    else:
        overflow = end - total_points
        window = np.concatenate([series[start:], series[:overflow]], axis=0)

    return window, start

@app.get("/")
def root():
    return {"message": "Satellite Telemetry Backend running"}

@app.get("/health")
def health():
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
    
    health_data = {
        "status": "healthy",
        "cuda": cuda_available,
        "device": device_name,
    }
    
    if cuda_available:
        try:
            health_data["vram_total"] = f"{torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB"
            health_data["vram_allocated"] = f"{torch.cuda.memory_allocated(0) / (1024**3):.2f} GB"
        except Exception:
            pass
            
    return health_data

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
    dataset = config.get("dataset", "")
    channels = _list_available_channels(dataset)
    if not channels:
        channels = [f"T-{i}" for i in range(1, 56)]
    return {"channels": channels}


@app.get("/telemetry/{channel}")
def get_telemetry(channel: str, offset: int = 0, length: int = 200, step: int = 50):
    try:
        series = _load_channel_series(channel)
        window, start = _slice_replay_window(series, offset=offset, length=length)
        metadata = _load_channel_metadata()
        total_points = int(series.shape[0])
        next_offset = (start + max(1, step)) % total_points

        return {
            "channel": channel,
            "data": window.round(6).tolist(),
            "offset": start,
            "next_offset": next_offset,
            "total_points": total_points,
            "dataset": metadata.get(channel, load_config().get("dataset", "unknown")),
            "source": "recorded_telemetry_replay",
            "live": False,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
