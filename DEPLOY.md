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

The first run may take several minutes because Ollama downloads `llama3`. The `ollama_data` Docker volume keeps that model cached for later runs.

## Direct Docker Run

After building the image:

```bash
docker build -t satellite-telemetry-anomaly-detection:latest .
docker run --gpus all --name satellite-telemetry -p 80:80 -p 8000:8000 -p 8001:8001 -p 11434:11434 -v satellite_ollama:/root/.ollama satellite-telemetry-anomaly-detection:latest
```

If you do not have NVIDIA GPU support, remove `--gpus all`. Inference still runs on CPU.

## API Keys

You can add API keys from the Settings UI. With Compose, `.env` and `Middleware/.env` are mounted into the container so saved keys persist across restarts.

## Split Deployment

The old multi-container setup is preserved in `docker-compose.split.yml`:

```bash
docker compose -f docker-compose.split.yml up -d --build
```

Use that only if you specifically want separate frontend, middleware, backend, and Ollama containers.
