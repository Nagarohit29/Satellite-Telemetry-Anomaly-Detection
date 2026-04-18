import sys
import os
import numpy as np

# Add Backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from infer import run_inference

def test_inference():
    print("Testing inference with univariate data...")
    # Generate 100 points of dummy data (univariate)
    dummy_data = np.random.randn(100, 1)
    
    try:
        result = run_inference(dummy_data)
        print("Inference successful!")
        print(f"Device: {result['device']}")
        print(f"Total windows: {result['total_windows']}")
        print(f"Anomaly count: {result['anomaly_count']}")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Inference failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_inference()
    if not success:
        sys.exit(1)
