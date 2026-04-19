import torch
import numpy as np
import yaml
import os
import logging
from src.models import TranAD
from src.constants import *

logger = logging.getLogger(__name__)

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
    model_path = os.path.join(
        os.path.dirname(__file__),
        'checkpoints',
        f"{config['model']}_{config['dataset']}",
        'model.ckpt'
    )
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model checkpoint not found at {model_path}. Please train the model first.")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        logger.info(f"✅ CUDA is available. Using device: {torch.cuda.get_device_name(0)}")
    else:
        logger.warning("⚠️ CUDA not detected. Falling back to CPU.")
    
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

def run_inference(data: np.ndarray):
    config = load_config()
    model, device, expected_feats = load_model(config)
    
    # Ensure input data matches model dimensions
    input_feats = data.shape[1]
    if input_feats != expected_feats:
        logger.warning(f"Adapting input features ({input_feats}) to match model expectation ({expected_feats}). Results may be unreliable.")
        if input_feats < expected_feats:
            # Pad with zeros
            padding = np.zeros((data.shape[0], expected_feats - input_feats))
            data = np.hstack([data, padding])
        else:
            # Truncate
            data = data[:, :expected_feats]
    
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