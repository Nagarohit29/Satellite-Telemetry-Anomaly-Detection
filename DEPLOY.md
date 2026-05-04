# Satellite Telemetry Anomaly Detection: One-Image Deployment

This project now builds as one Docker image that runs everything inside one container:

- React frontend on port 80
- FastAPI middleware on port 8000
- ML backend on port 8001
- Ollama on port 11434

The default `docker-compose.yml` starts only this single container.

## Prerequisites

- Docker Desktop or Docker Engine
- NVIDIA Container Toolkit if you want GPU support
- Enough disk space for the CUDA/PyTorch image and the Ollama model cache

## Recommended Run

From the project root:

```bash
docker compose up -d --build
```

Open:

- Dashboard: http://localhost
- Middleware API: http://localhost:8000/docs
- Backend API: http://localhost:8001/docs
- Ollama API: http://localhost:11434

On first run, the same monolithic container pulls `llama3.2` into the named `ollama_data` volume, matching the earlier `1.0` behavior. Later restarts reuse that cached model instead of downloading it again. Startup can still take several minutes while the model pull completes, Triton becomes healthy, and the rest of the stack comes online. On the GPU path, the first local Ollama request may spend extra time loading the model into VRAM.

## Direct Docker Run

After building or pulling the image from Docker Hub, use one of the following commands:

### Option 1: Run with NVIDIA GPU (Recommended)
*Requires an NVIDIA GPU and the NVIDIA Container Toolkit.*

```bash
docker run --gpus all \
  --name satellite-telemetry \
  -p 80:80 \
  -p 8000:8000 \
  -p 8001:8001 \
  -p 11434:11434 \
  -p 8008:8008 \
  -v ollama_data:/root/.ollama \
  -d nagarohit/satellite-telemetry-anomaly-detection:2.0
```

### Option 2: Run with CPU Only
*Deep learning inference will automatically fall back to CPU processing.*

```bash
docker run \
  --name satellite-telemetry \
  -p 80:80 \
  -p 8000:8000 \
  -p 8001:8001 \
  -p 11434:11434 \
  -p 8008:8008 \
  -v ollama_data:/root/.ollama \
  -d nagarohit/satellite-telemetry-anomaly-detection:2.0
```

## API Keys

You can add API keys from the Settings UI. Configurations and keys are stored ephemerally within the container. They will persist if the container is stopped and restarted, but will be securely destroyed if the container is removed (`docker rm`). The Ollama models themselves are persisted to a named volume (`ollama_data`) so you don't have to re-download massive AI models on a fresh run.

## Split Deployment

The old multi-container setup is preserved in `docker-compose.split.yml`:

```bash
docker compose -f docker-compose.split.yml up -d --build
```

Use that only if you specifically want separate frontend, middleware, backend, and Ollama containers.
