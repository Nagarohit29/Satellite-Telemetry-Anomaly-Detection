# 🚀 Satellite Telemetry Anomaly Detection: Deployment Guide

This project is fully Dockerized and available as a monolithic image. You can run the entire system (Frontend, Middleware, Backend, and AI Models) with a single command.

## 🛠 Prerequisites
- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux).
- **NVIDIA GPU Support**: Ensure you have the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed if you want to use GPU acceleration.
- **AI API Key**: A [Google Gemini API Key](https://aistudio.google.com/) is recommended for the best experience.

---

## 🏃 Quick Start (Zero Config)
If you just want to see the app in action without worrying about folders, run this:

```bash
docker run -p 80:80 -p 11434:11434 \
  --gpus all \
  -e GOOGLE_API_KEY="your_api_key_here" \
  nagarohit/satellite-telemetry-full:latest
```

**Note:** The first time you run this, it will automatically download the `llama3` model via Ollama. This may take 5-10 minutes.

---

## 💾 Recommended Run (Persistent Data)
Use this method if you want to keep your trained models, telemetry data, and detection results saved on your computer even after the container is deleted.

### 1. Create a local folder
Create a folder for the project data (e.g., `C:\STAD_Data`).

### 2. Run with Volumes
```bash
docker run -p 80:80 -p 8000:8000 -p 8001:8001 -p 11434:11434 \
  --gpus all \
  -v "C:\STAD_Data\checkpoints:/app/Backend/checkpoints" \
  -v "C:\STAD_Data\data:/app/Backend/data" \
  -v "C:\STAD_Data\results:/app/Backend/results" \
  -e GOOGLE_API_KEY="your_api_key_here" \
  nagarohit/satellite-telemetry-full:latest
```

---

## 📦 Using Docker Compose (Pro Way)
We recommend using the included `docker-compose.yml` for the easiest management.

1.  Navigate to the project root.
2.  Run:
    ```bash
    docker-compose up -d
    ```

---

## 🌐 Accessing the App
Once the container is running:
- **Dashboard**: [http://localhost](http://localhost)
- **Middleware API**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend API**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Ollama**: [http://localhost:11434](http://localhost:11434)

## 🐳 Image Details
- **Docker Hub**: `nagarohit/satellite-telemetry-full:latest`
- **Size**: ~20 GB (Includes CUDA, PyTorch, and Ollama)
- **Vulnerabilities**: Standard for ML images (comes from NVIDIA/PyTorch base layers).
