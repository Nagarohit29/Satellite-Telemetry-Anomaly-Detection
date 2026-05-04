import torch
import numpy as np
import yaml
import os
import logging
import threading
from pathlib import Path
from src.models import TranAD
from src.constants import *

logger = logging.getLogger(__name__)
_MODEL_CACHE = None
_MODEL_CACHE_LOCK = threading.Lock()


def select_inference_device() -> torch.device:
    """Pick the inference device from env/config with CUDA auto-detection."""
    requested = os.getenv("INFERENCE_DEVICE", "auto").strip().lower()

    if requested == "cpu":
        logger.info("Using CPU for inference (INFERENCE_DEVICE=cpu).")
        return torch.device("cpu")

    if requested in ("auto", "cuda", "gpu"):
        if torch.cuda.is_available():
            logger.info("Using CUDA for inference.")
            return torch.device("cuda")
        if requested in ("cuda", "gpu"):
            logger.warning("CUDA was requested for inference but is not available. Falling back to CPU.")

    logger.info("Using CPU for inference.")
    return torch.device("cpu")

def load_config():
    """Load configuration from config.yaml, checking script directory first."""
    possible_paths = [
        "config.yaml",
        os.path.join(os.path.dirname(__file__), "config.yaml"),
        os.getenv("CONFIG_PATH", "")
    ]
    for path in possible_paths:
        if path and os.path.exists(path):
            with open(path, "r") as f:
                return yaml.safe_load(f)
    raise FileNotFoundError("config.yaml not found in Backend directory or root.")

def load_model(config):
    model_path = get_model_path(config)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model checkpoint not found at {model_path}. Please train the model first.")
    
    device = select_inference_device()
    
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    state_dict = checkpoint.get('model_state_dict', checkpoint)
    
    # Infer feature count from the FCN layer in the state dict
    # TranAD has a final linear layer: nn.Linear(2 * feats, feats)
    # The weight shape is [out_features, in_features] -> [feats, 2 * feats]
    if 'fcn.0.weight' in state_dict:
        expected_feats = state_dict['fcn.0.weight'].shape[0]
    elif 'fcn.weight' in state_dict:
        expected_feats = state_dict['fcn.weight'].shape[0]
    else:
        # Fallback to a default if we can't infer it (though it should be there)
        logger.warning("Could not infer feature count from checkpoint, defaulting to 25.")
        expected_feats = 25

    logger.debug(f"Detected model features: {expected_feats}")
    
    # Load the model architecture
    from src.models import TranAD
    model = TranAD(expected_feats)
    model.load_state_dict(state_dict)
    model = model.to(device)
    model.eval()
    return model, device, expected_feats


def get_model_path(config) -> str:
    return os.path.join(
        os.path.dirname(__file__),
        "checkpoints",
        f"{config['model']}_{config['dataset']}",
        "model.ckpt",
    )


def get_model_signature(config) -> dict:
    model_path = get_model_path(config)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model checkpoint not found at {model_path}. Please train the model first.")

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    state_dict = checkpoint.get("model_state_dict", checkpoint)

    if "fcn.0.weight" in state_dict:
        expected_feats = int(state_dict["fcn.0.weight"].shape[0])
    elif "fcn.weight" in state_dict:
        expected_feats = int(state_dict["fcn.weight"].shape[0])
    else:
        logger.warning("Could not infer feature count from checkpoint, defaulting to 25.")
        expected_feats = 25

    window_size = int(config["inference"]["window_size"])
    threshold = float(os.getenv("INFERENCE_THRESHOLD", config["inference"]["threshold"]))
    return {
        "expected_feats": expected_feats,
        "window_size": window_size,
        "threshold": threshold,
        "model_path": model_path,
    }

def get_cached_model(config):
    """Load the TranAD checkpoint once per process instead of once per request."""
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        with _MODEL_CACHE_LOCK:
            if _MODEL_CACHE is None:
                _MODEL_CACHE = load_model(config)
    return _MODEL_CACHE


def adapt_input_features(data: np.ndarray, expected_feats: int) -> tuple[np.ndarray, int]:
    input_feats = int(data.shape[1])
    if input_feats == expected_feats:
        return data, input_feats

    logger.warning(
        "Adapting input features (%s) to match model expectation (%s). Results may be unreliable.",
        input_feats,
        expected_feats,
    )
    if input_feats < expected_feats:
        padding = np.zeros((data.shape[0], expected_feats - input_feats), dtype=data.dtype)
        return np.hstack([data, padding]), input_feats
    return data[:, :expected_feats], expected_feats


class TritonTranADWrapper(torch.nn.Module):
    """TorchScript-friendly TranAD wrapper that emits anomaly scores for Triton."""

    def __init__(self, model: torch.nn.Module, window_size: int):
        super().__init__()
        self.model = model
        self.window_size = window_size

    def forward(self, data: torch.Tensor) -> torch.Tensor:
        windows = data.unfold(0, self.window_size, 1)
        num_windows = data.shape[0] - self.window_size
        windows = windows[:num_windows].permute(0, 2, 1).contiguous()
        reconstructed = self.model(windows, windows)[0]
        return ((windows - reconstructed) ** 2).mean(dim=(1, 2))


def export_triton_model(output_path: str | os.PathLike[str]) -> dict:
    config = load_config()
    signature = get_model_signature(config)
    model, _device, expected_feats = load_model(config)
    model = model.to("cpu")
    model.eval()

    wrapper = TritonTranADWrapper(model, signature["window_size"]).eval()
    scripted = torch.jit.script(wrapper)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scripted.save(str(output_path))

    return {
        "model_path": str(output_path),
        "expected_feats": expected_feats,
        "window_size": signature["window_size"],
        "threshold": signature["threshold"],
    }

def run_inference(data: np.ndarray):
    config = load_config()
    model, device, expected_feats = get_cached_model(config)
    
    # Ensure input data matches model dimensions
    data, input_feats = adapt_input_features(data, expected_feats)
    
    window_size = config["inference"]["window_size"]
    threshold = float(os.getenv("INFERENCE_THRESHOLD", config["inference"]["threshold"]))

    tensor = torch.FloatTensor(data).to(device)

    scores = []
    with torch.no_grad():
        for i in range(len(tensor) - window_size):
            window = tensor[i:i + window_size].unsqueeze(0)
            output = model(window, window)
            if isinstance(output, tuple):
                output = output[0]
            # Use only the original number of features for the score if padded
            score = torch.mean((window[:, :, :input_feats] - output[:, :, :input_feats]) ** 2).item()
            scores.append(score)

    anomalies = [
        {"index": i, "score": round(s, 6), "anomaly": s > threshold}
        for i, s in enumerate(scores)
    ]

    return {
        "scores": scores,
        "anomalies": anomalies,
        "threshold": threshold,
        "device": str(device),
        "total_windows": len(scores),
        "anomaly_count": sum(1 for a in anomalies if a["anomaly"])
    }

if __name__ == "__main__":
    dummy = np.random.randn(200, 25)
    result = run_inference(dummy)
    print(f"Anomaly count: {result['anomaly_count']} / {result['total_windows']}")
