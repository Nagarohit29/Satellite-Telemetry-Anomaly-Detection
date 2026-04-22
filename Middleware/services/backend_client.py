import httpx
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
INFER_TIMEOUT_SECONDS = float(os.getenv("INFER_TIMEOUT_SECONDS", "180"))

async def call_infer(channel: str, data: list) -> dict:
    try:
        async with httpx.AsyncClient(timeout=INFER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{BACKEND_URL}/infer",
                json={"channel": channel, "data": data}
            )
            if response.status_code != 200:
                detail = response.json().get('detail', 'Inference failed')
                raise Exception(f"Backend Error: {detail}")
            return response.json()
    except httpx.ConnectError:
        raise Exception(f"Cannot connect to backend at {BACKEND_URL}")
    except httpx.TimeoutException:
        raise Exception(f"Backend request timed out after {INFER_TIMEOUT_SECONDS:.0f}s")

async def call_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BACKEND_URL}/health")
            response.raise_for_status()
            return response.json()
    except Exception:
        return {"status": "unreachable", "cuda": False, "device": "unknown"}

async def call_channels() -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BACKEND_URL}/channels")
            response.raise_for_status()
            return response.json()
    except Exception:
        return {"channels": [f"T-{i}" for i in range(1, 56)]}


async def call_telemetry(channel: str, offset: int = 0, length: int = 200, step: int = 50) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BACKEND_URL}/telemetry/{channel}",
                params={"offset": offset, "length": length, "step": step},
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise Exception(f"Cannot connect to backend at {BACKEND_URL}")
    except httpx.TimeoutException:
        raise Exception("Backend telemetry request timed out")

async def call_train(dataset: str = "SMAP", epochs: int = 5) -> dict:
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/train",
                json={"dataset": dataset, "epochs": epochs}
            )
            if response.status_code != 200:
                detail = response.json().get('detail', 'Training failed')
                raise Exception(f"Backend Error: {detail}")
            return response.json()
    except Exception as e:
        raise Exception(f"Training failed: {str(e)}")
