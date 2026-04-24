# Satellite Telemetry Anomaly Detection (STAD)

A comprehensive full-stack solution for monitoring satellite telemetry and detecting anomalies using state-of-the-art Deep Transformer Networks. This project combines advanced machine learning with a modern web interface and AI-driven incident analysis.

## 🚀 Overview

The STAD system is designed to handle high-dimensional, multivariate time series data from spacecraft subsystems. It provides real-time detection, visualization, and intelligent reporting to assist satellite operations teams in identifying and diagnosing potential failures.

### Key Features
- **Advanced AI Models**: Powered by **TranAD** (Transformer-based Anomaly Detection) and several baseline models (GDN, USAD, OmniAnomaly, etc.).
- **Interactive Dashboard**: Real-time telemetry visualization using React and Recharts.
- **AI Incident Reports**: Automated summary generation using LLMs (Gemini, GPT-4, Claude, or local Ollama).
- **Conversational Assistant**: An AI analyst to help investigate anomalies and subsystem health.
- **Dockerized Infrastructure**: Seamless deployment using Docker Compose with GPU support.

## 🏗️ Architecture

The project is divided into three primary components:

### 1. Backend (AI Engine)
Located in [`/Backend`](./Backend), this service handles the core machine learning tasks.
- **Core Engine**: Based on the **TranAD** research project.
- **Technology**: PyTorch, NumPy, Pandas, FastAPI.
- **Capabilities**: Training and inference for multiple anomaly detection architectures.
- **Attribution**: The core ML logic is refactored from the [TranAD repository](https://github.com/imperial-qore/TranAD) by Shreshth Tuli et al. (VLDB 2022).

### 2. Middleware (Orchestrator)
Located in [`/Middleware`](./Middleware), this service acts as the brain of the application.
- **Logic**: Manages communication between the UI, the AI Engine, and LLM providers.
- **AI Integration**: Uses **LiteLLM** to provide a unified interface for various AI providers.
- **Reporting**: Generates professional incident reports based on detected anomalies.

### 3. Frontend (UI)
Located in [`/Frontend`](./Frontend), a modern web interface for operators.
- **Tech Stack**: React 18, Vite, Recharts, TailwindCSS.
- **Features**: Telemetry heatmaps, anomaly charts, and an integrated AI chat interface.

## 🛠️ Getting Started

### Prerequisites
- Docker and Docker Compose
- NVIDIA GPU with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) (optional, for acceleration)
- Python 3.10+ (for local development)

### Quick Start (Docker)
1. Clone the repository.
2. Configure your environment variables in a `.env` file (see below).
3. Start the system:
   ```bash
   docker-compose up --build
   ```
4. Access the dashboard at `http://localhost`.

### Run From Docker Hub
If you do not want to clone the repository, you can pull and run the published
single-container image directly from Docker Hub.

1. Pull the image:
   ```bash
   docker pull <your-dockerhub-username>/satellite-telemetry-anomaly-detection:latest
   ```
2. Run the container:
   ```bash
   docker run --gpus all --name satellite-telemetry \
     -p 80:80 -p 8000:8000 -p 8001:8001 -p 11434:11434 \
     <your-dockerhub-username>/satellite-telemetry-anomaly-detection:latest
   ```
3. Open the application:
   - Frontend: `http://localhost`
   - Middleware API: `http://localhost:8000`
   - Backend API: `http://localhost:8001`
   - Ollama API: `http://localhost:11434`

Notes for Docker Hub users:
- The dashboard currently replays recorded SMAP telemetry data bundled with the image.
- Ollama Cloud keys are session-only by default and are not written to `.env`
  unless you explicitly change that behavior in the app.
- NVIDIA Container Toolkit is required for GPU access with `--gpus all`.

### Local Development Setup
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the services individually (Backend on 8001, Middleware on 8000, Frontend on 3000).

## ⚙️ Configuration

Create a `.env` file in the root directory with the following variables:

```env
# AI Providers (At least one required for reporting)
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Backend Config
DATASET=SMAP
WINDOW_SIZE=10
THRESHOLD=0.2
BACKEND_URL=http://localhost:8001

# Ollama (Optional for local AI)
OLLAMA_MODEL=llama3.2
```

## 📜 Attribution & License

This project incorporates research code from the following source:
- **Project**: [TranAD](https://github.com/imperial-qore/TranAD)
- **Paper**: *TranAD: Deep Transformer Networks for Anomaly Detection in Multivariate Time Series Data*
- **Authors**: Shreshth Tuli, Giuliano Casale, Nicholas R. Jennings
- **Conference**: Proceedings of VLDB (Vol 15, No 6), 2022.

The Backend code is licensed under the **BSD 3-Clause License** (Copyright (c) 2022, Shreshth Tuli). See the [`Backend/LICENSE`](./Backend/LICENSE) for full details.
