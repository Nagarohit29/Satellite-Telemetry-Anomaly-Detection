import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import yaml
import os
import sys
import csv
import json
import subprocess
import urllib.request
from functools import lru_cache
from dotenv import load_dotenv
from triton_client import infer_scores, health as triton_health

try:
    import torch  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional runtime dependency in monolith v2
    torch = None

# Load environment variables
load_dotenv()

app = FastAPI(title="Satellite Telemetry Backend API", version="2.0.0")

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


def _detect_compute() -> tuple[bool, str]:
    if torch is not None:
        try:
            cuda_available = bool(torch.cuda.is_available())
            if cuda_available:
                return True, str(torch.cuda.get_device_name(0))
        except Exception:
            pass

    metrics_url = os.getenv("TRITON_METRICS_URL", "").strip()
    if metrics_url:
        try:
            with urllib.request.urlopen(metrics_url, timeout=3.0) as response:
                metrics_text = response.read().decode("utf-8", errors="replace")
            if "nv_gpu_utilization" in metrics_text or "nv_gpu_power_usage" in metrics_text:
                return True, "NVIDIA GPU"
        except Exception:
            pass

    nvidia_smi = "nvidia-smi.exe" if os.name == "nt" else "nvidia-smi"
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            gpu_name = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
            if gpu_name:
                return True, gpu_name
    except Exception:
        pass

    return False, "CPU"


def _runtime_signature_path() -> str:
    explicit_path = os.getenv("TRITON_EXPORT_MANIFEST")
    if explicit_path:
        return explicit_path

    candidates = [
        os.path.join("/models", "tranad", "export_manifest.json"),
        os.path.join(_backend_root(), "..", "triton", "model_repository", "tranad", "export_manifest.json"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


@lru_cache(maxsize=1)
def _load_runtime_signature() -> dict:
    manifest_path = _runtime_signature_path()
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "expected_feats": int(data["expected_feats"]),
            "window_size": int(data["window_size"]),
            "threshold": float(os.getenv("INFERENCE_THRESHOLD", data["threshold"])),
            "model_path": data.get("model_path"),
            "manifest_path": manifest_path,
        }

    from infer import get_model_signature, load_config as load_infer_config

    config = load_infer_config()
    signature = get_model_signature(config)
    signature["manifest_path"] = manifest_path
    return signature


def adapt_input_features(data: np.ndarray, expected_feats: int) -> tuple[np.ndarray, int]:
    input_feats = int(data.shape[1])
    if input_feats == expected_feats:
        return data, input_feats

    if input_feats < expected_feats:
        padding = np.zeros((data.shape[0], expected_feats - input_feats), dtype=data.dtype)
        return np.hstack([data, padding]), input_feats
    return data[:, :expected_feats], expected_feats

@app.get("/")
def root():
    return {"message": "Satellite Telemetry Backend running"}

@app.get("/health")
def health():
    cuda_available, device_name = _detect_compute()
    triton_state = triton_health()
    
    health_data = {
        "status": "healthy" if triton_state["ready"] and triton_state["model_ready"] else "degraded",
        "cuda": cuda_available,
        "device": device_name,
        "inference_engine": "triton",
        "triton_ready": triton_state["ready"],
        "triton_model_ready": triton_state["model_ready"],
        "triton_url": triton_state["url"],
        "triton_model_name": triton_state["model_name"],
    }
    
    if cuda_available and torch is not None:
        try:
            health_data["vram_total"] = f"{torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB"
            health_data["vram_allocated"] = f"{torch.cuda.memory_allocated(0) / (1024**3):.2f} GB"
        except Exception:
            pass
            
    return health_data

@app.post("/infer")
def infer(req: InferRequest):
    try:
        data = np.array(req.data)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        signature = _load_runtime_signature()
        if int(data.shape[0]) <= int(signature["window_size"]):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Telemetry sequence must contain more than {signature['window_size']} points "
                    "for sliding-window inference."
                ),
            )

        prepared, original_feats = adapt_input_features(data.astype(np.float32, copy=False), signature["expected_feats"])
        print(
            f"Forwarding inference request for channel {req.channel} "
            f"to Triton with shape {prepared.shape}"
        )
        scores = infer_scores(prepared)
        threshold = float(signature["threshold"])
        cuda_available, _device_name = _detect_compute()
        anomalies = [
            {"index": i, "score": round(float(score), 6), "anomaly": float(score) > threshold}
            for i, score in enumerate(scores)
        ]
        return {
            "channel": req.channel,
            "scores": scores,
            "anomalies": anomalies,
            "threshold": threshold,
            "device": "cuda" if cuda_available else "cpu",
            "input_features": original_feats,
            "expected_features": signature["expected_feats"],
            "window_size": signature["window_size"],
            "total_windows": len(scores),
            "anomaly_count": sum(1 for a in anomalies if a["anomaly"]),
            "inference_engine": "triton",
        }
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
    if os.getenv("ENABLE_TRAINING", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(
            status_code=501,
            detail="Training is disabled in this runtime image. Use the development environment to retrain models.",
        )
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
