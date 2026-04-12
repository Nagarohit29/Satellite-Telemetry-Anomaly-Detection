import torch
import numpy as np
import yaml
import os
from src.models import TranAD
from src.constants import *

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def load_model(config):
    model_path = os.path.join(
        config["paths"]["model_dir"],
        f"{config['model']}_{config['dataset']}.pt"
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = torch.load(model_path, map_location=device)
    model.eval()
    return model, device

def run_inference(data: np.ndarray):
    config = load_config()
    model, device = load_model(config)
    window_size = config["inference"]["window_size"]
    threshold = config["inference"]["threshold"]

    tensor = torch.FloatTensor(data).to(device)

    scores = []
    with torch.no_grad():
        for i in range(len(tensor) - window_size):
            window = tensor[i:i + window_size].unsqueeze(0)
            output = model(window, window)
            if isinstance(output, tuple):
                output = output[0]
            score = torch.mean((window - output) ** 2).item()
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