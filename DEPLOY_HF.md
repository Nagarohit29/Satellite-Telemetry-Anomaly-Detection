# Deploying STAD-AI to Hugging Face Spaces (Free Tier)

This guide deploys your full Satellite Telemetry Anomaly Detection system to Hugging Face Spaces **completely for free**.

**What you get:** 16GB RAM, 2 vCPUs, a public URL, automatic Docker builds.

---

## Prerequisites

- Your Hugging Face Space is already created at: `https://huggingface.co/spaces/Nagarohit/stad-ai`
- You have a Hugging Face access token with **write** permissions from: https://huggingface.co/settings/tokens

---

## Step-by-Step Deployment

### Step 1: Add the HF Space as a Git Remote

From your project root (`c:\Naga\projects\SatelliteTelemetryAnomalyDetection`), run:

```powershell
git remote add hf https://huggingface.co/spaces/Nagarohit/stad-ai
```

### Step 2: Commit the Latest Changes

```powershell
git add .
git commit -m "Add Hugging Face Spaces deployment config"
```

### Step 3: Create an HF Deployment Branch

We need a branch where `Dockerfile.hf` becomes `Dockerfile` (HF only looks for `Dockerfile`):

```powershell
git checkout -b hf-deploy
copy Dockerfile.hf Dockerfile
git add Dockerfile
git commit -m "Use HF-optimized Dockerfile for Spaces deployment"
```

### Step 4: Force Push to Hugging Face

```powershell
git push hf hf-deploy:main --force
```

When prompted for credentials:
- **Username:** Your Hugging Face username (e.g., `Nagarohit`)
- **Password:** Your Hugging Face access token (NOT your HF password)

### Step 5: Switch Back to Main

```powershell
git checkout main
```

### Step 6: Monitor the Build

1. Go to https://huggingface.co/spaces/Nagarohit/stad-ai
2. Click the **"Building"** status badge or the **Logs** tab
3. The Docker build will take **10-20 minutes** (it installs PyTorch, Triton, Ollama, etc.)
4. Once status shows **"Running"**, your app is live!

---

## After Deployment

### Accessing Your App
Your app will be live at:
```
https://nagarohit-stad-ai.hf.space
```

### Adding API Keys (Optional)
To use cloud LLMs (Gemini, OpenAI) instead of local Ollama for faster responses:
1. Go to Space **Settings** → **Variables and secrets**
2. Add secrets like `GEMINI_API_KEY`, `OPENAI_API_KEY`, etc.
3. The space will auto-restart with the new keys

### Future Updates
Whenever you make changes and want to redeploy:
```powershell
git checkout hf-deploy
git merge main
copy Dockerfile.hf Dockerfile
git add Dockerfile
git commit -m "Update HF deployment"
git push hf hf-deploy:main --force
git checkout main
```

### Cold Starts
Free-tier spaces go to sleep after ~48 hours of inactivity. The first visitor after a sleep period will trigger a cold start (~2-5 minutes). This is normal for the free tier.

---

## Architecture on Hugging Face

```
Port 7860 (exposed to internet by HF)
    │
    ├── Nginx (reverse proxy)
    │     ├── /           → React Frontend (static files)
    │     ├── /api/*      → Middleware FastAPI (port 8000)
    │     └── /backend/*  → Backend FastAPI (port 8001)
    │
    ├── Triton Inference Server (port 8008, internal)
    │     └── TranAD model for anomaly detection
    │
    └── Ollama (port 11434, internal)
          └── llama3.2 for natural language analysis
```
