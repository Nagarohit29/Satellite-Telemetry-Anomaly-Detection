from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from dotenv import load_dotenv
import time as _time
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from starlette.middleware.gzip import GZipMiddleware

# Force reload environment variables (checks project root .env for Web UI overrides)
def reload_env(path=None):
    """Dynamically reload environment variables from the project env files."""
    config_env = "/app/config/.env"
    root_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    middleware_env = os.path.join(os.path.dirname(__file__), '.env')
    
    # Load in order so more specific files can override defaults.
    targets = [target for target in [path, config_env, root_env, middleware_env] if target]
    loaded = set()
    for target in targets:
        if target in loaded:
            continue
        if os.path.exists(target):
            load_dotenv(target, override=True)
            loaded.add(target)
    load_dotenv()

# Initial load
reload_env()

# Suppress litellm's verbose debug output
os.environ["LITELLM_LOG"] = "ERROR"

def validate_env_vars():
    """Log which AI providers are configured (informational only)."""
    providers = {
        "GEMINI_API_KEY": "Google Gemini",
        "OPENAI_API_KEY": "OpenAI",
        "ANTHROPIC_API_KEY": "Anthropic Claude",
    }
    configured = [name for var, name in providers.items() if os.getenv(var)]
    missing = [name for var, name in providers.items() if not os.getenv(var)]
    
    if configured:
        print(f"INFO: Configured AI providers: {', '.join(configured)}")
    if missing:
        print(f"INFO: Unconfigured AI providers (add keys via Settings): {', '.join(missing)}")
    
    if not os.getenv("BACKEND_URL"):
        print("INFO: BACKEND_URL not set, using default: http://localhost:8001")

app = FastAPI(title="Satellite Telemetry Middleware", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Prometheus Metrics ──
MW_REQUEST_COUNT = Counter('middleware_requests_total', 'Total requests', ['method', 'path', 'status'])
MW_REQUEST_LATENCY = Histogram('middleware_request_duration_seconds', 'Request latency', ['method', 'path'])
MW_ACTIVE_REQUESTS = Gauge('middleware_active_requests', 'Active concurrent requests')

@app.middleware("http")
async def metrics_middleware(request, call_next):
    MW_ACTIVE_REQUESTS.inc()
    start = _time.monotonic()
    response = await call_next(request)
    duration = _time.monotonic() - start
    path = request.url.path.split('?')[0]
    MW_REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
    MW_REQUEST_LATENCY.labels(request.method, path).observe(duration)
    response.headers['X-Request-Duration-Ms'] = f'{duration * 1000:.1f}'
    MW_ACTIVE_REQUESTS.dec()
    return response

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routers import predict, alerts, channels, chat, config
from services.backend_client import call_health

app.include_router(predict.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(channels.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(config.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Middleware running"}

@app.get("/health")
async def health():
    return await call_health()

@app.get("/api/health")
async def api_health():
    return await call_health()

@app.get('/metrics')
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    try:
        validate_env_vars()
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        sys.exit(1)
