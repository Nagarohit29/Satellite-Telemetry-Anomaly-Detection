# Implementation Plan - Fix AI Model Selection and Environment Logic

The user is reporting that the AI model selection is broken: OpenAI is being used even when not selected, and Ollama is not working correctly. Additionally, there is a distinction between **Local Ollama** (running via Docker/locally) and **Cloud Ollama** (via API).

## User Review Required

> [!IMPORTANT]
> **Refined AI Selection Logic**: 
> 1. **Default Behavior**: If no model is selected (or "Auto" is used), the system will use **Local Ollama** by default.
> 2. **Explicit Choice**: Cloud APIs (OpenAI, Gemini, Claude, **Cloud Ollama**) will **only** be used if you specifically select them in the settings.
> 3. **Automatic Fallback**: If you select a Cloud model but its API key is missing or invalid, the system will automatically fall back to **Local Ollama**.

> [!IMPORTANT]
> **Docker Integration**: I will ensure that the default `OLLAMA_API_BASE` for Docker environments is `http://ollama:11434`, which is the standard service name in Docker Compose.

## Proposed Changes

### 1. Root Configuration
#### [MODIFY] [.env](file:///c:/Naga/projects/SatelliteTelemetryAnomalyDetection/.env)
- Remove the invalid `OLLAMA_API_KEY='docker-compose up --build satellite-app'` value.
- Set `OLLAMA_API_BASE=http://ollama:11434` as the default (commented out) but provide clear documentation for local vs docker usage.

### 2. Middleware Component
#### [MODIFY] [llm_service.py](file:///c:/Naga/projects/SatelliteTelemetryAnomalyDetection/Middleware/services/llm_service.py)
- **Separate Local vs Cloud Ollama**: Update `_get_ollama_urls` to strictly distinguish between Cloud (via `OLLAMA_API_KEY`) and Local (via `OLLAMA_API_BASE`).
- **Improved Reachability Check**: Enhance `_is_ollama_reachable` to check `http://ollama:11434` (Docker), `http://127.0.0.1:11434` (Local), and `http://localhost:11434`.
- **Strict Default to Local**: Modify `_build_models_to_try` so it defaults to Local Ollama if no preference is given.
- **Explicit Cloud Use**: Only include Cloud models (OpenAI, Gemini, Claude, Cloud Ollama) if they are explicitly selected AND have valid keys.
- **Dynamic Pathing**: Ensure `.env` discovery works across Windows and Linux/Docker.

#### [MODIFY] [main.py](file:///c:/Naga/projects/SatelliteTelemetryAnomalyDetection/Middleware/main.py)
- Ensure `reload_env` correctly finds the `.env` file regardless of the execution context (Windows local vs Docker).

## Verification Plan

### Automated Tests
- Test `/api/health` to verify backend connectivity.
- Test `/api/predict` with `model_preference="ollama"` to ensure it hits the local/docker instance.
- Test `/api/predict` with `model_preference="openai"` to verify cloud integration.

### Manual Verification
- Verify that the "CUDA: enabled" status is correctly reported in the UI (already fixed, but worth re-checking).
- Verify that "Local Ollama" is used by default when OpenAI is unselected.
