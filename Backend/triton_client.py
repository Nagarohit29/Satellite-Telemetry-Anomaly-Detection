import json
import os
import urllib.error
import urllib.request

import numpy as np


TRITON_URL = os.getenv("TRITON_URL", "http://localhost:8000").rstrip("/")
TRITON_MODEL_NAME = os.getenv("TRITON_MODEL_NAME", "tranad")


def _triton_endpoint(path: str) -> str:
    return f"{TRITON_URL}{path}"


def health() -> dict:
    ready = False
    model_ready = False
    detail = None
    try:
        with urllib.request.urlopen(_triton_endpoint("/v2/health/ready"), timeout=3.0) as response:
            ready = response.status == 200
    except Exception as exc:  # pragma: no cover - network path
        detail = str(exc)

    try:
        with urllib.request.urlopen(_triton_endpoint(f"/v2/models/{TRITON_MODEL_NAME}/ready"), timeout=3.0) as response:
            model_ready = response.status == 200
    except Exception as exc:  # pragma: no cover - network path
        detail = detail or str(exc)

    return {
        "ready": ready,
        "model_ready": model_ready,
        "url": TRITON_URL,
        "model_name": TRITON_MODEL_NAME,
        "detail": detail,
    }


def infer_scores(data: np.ndarray) -> list[float]:
    payload = {
        "inputs": [
            {
                "name": "DATA",
                "shape": list(data.shape),
                "datatype": "FP32",
                "data": data.astype(np.float32, copy=False).reshape(-1).tolist(),
            }
        ],
        "outputs": [{"name": "SCORES"}],
    }

    request = urllib.request.Request(
        _triton_endpoint(f"/v2/models/{TRITON_MODEL_NAME}/infer"),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60.0) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Triton HTTP {exc.code}: {body[:400]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Triton at {TRITON_URL}: {exc.reason}") from exc

    outputs = {item["name"]: item for item in raw.get("outputs", [])}
    if "SCORES" not in outputs:
        raise RuntimeError(f"Triton response missing SCORES output: {raw}")
    return [float(score) for score in outputs["SCORES"].get("data", [])]
