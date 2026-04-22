import subprocess
import sys
import yaml
import os

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def train(dataset=None, epochs=None):
    config = load_config()
    model = config["model"]
    
    # Use provided values or fallback to config
    dataset = dataset or config["training"].get("dataset", config["dataset"])
    epochs = epochs or config["training"]["epochs"]

    print(f"Starting training: model={model}, dataset={dataset}, epochs={epochs}")

    cmd = [
        sys.executable, "main.py",
        "--model", model,
        "--dataset", dataset,
        "--retrain"
    ]

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print("Training completed successfully.")
    else:
        print("Training failed.")
        sys.exit(1)

if __name__ == "__main__":
    train()