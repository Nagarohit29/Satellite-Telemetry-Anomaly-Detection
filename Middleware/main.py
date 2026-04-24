from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from dotenv import load_dotenv

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

app = FastAPI(title="Satellite Telemetry Middleware", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
