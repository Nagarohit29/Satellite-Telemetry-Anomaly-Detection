from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging
from dotenv import set_key, unset_key

logger = logging.getLogger(__name__)
router = APIRouter()
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

class KeyUpdate(BaseModel):
    provider: str
    key: str

PROVIDER_TO_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": "OLLAMA_API_KEY"
}

# Minimum key length per provider (rejects obvious fakes like "test" or "123")
MIN_KEY_LENGTHS = {
    "gemini": 20,
    "openai": 20,
    "anthropic": 20,
    "ollama": 1,   # Ollama keys can be anything
}


@router.post("/config/keys")
async def update_key(data: KeyUpdate):
    provider = data.provider.lower()
    env_var = PROVIDER_TO_ENV.get(provider)
    if not env_var:
        raise HTTPException(status_code=400, detail="Invalid provider")

    # Basic validation — reject obviously fake keys
    min_len = MIN_KEY_LENGTHS.get(provider, 10)
    if len(data.key.strip()) < min_len:
        raise HTTPException(
            status_code=400,
            detail=f"API key too short. {provider.capitalize()} keys are typically longer than {min_len} characters."
        )

    clean_key = data.key.strip()

    # Ensure .env exists
    if not os.path.exists(ENV_PATH):
        open(ENV_PATH, 'a').close()

    # Set key in .env file for persistence across restarts
    set_key(ENV_PATH, env_var, clean_key)

    # Also inject into the running process for immediate use
    os.environ[env_var] = clean_key

    logger.info(f"API key updated for {provider} ({env_var})")
    return {"status": "success", "message": f"{provider.capitalize()} API key saved"}


@router.delete("/config/keys/{provider}")
async def delete_key(provider: str):
    env_var = PROVIDER_TO_ENV.get(provider.lower())
    if not env_var:
        raise HTTPException(status_code=400, detail="Invalid provider")

    if os.path.exists(ENV_PATH):
        unset_key(ENV_PATH, env_var)

    # Remove from current environment
    if env_var in os.environ:
        del os.environ[env_var]

    logger.info(f"API key removed for {provider} ({env_var})")
    return {"status": "success", "message": f"{provider.capitalize()} API key removed"}


@router.get("/config/keys/status")
async def key_status():
    """Returns which providers have keys configured (without exposing the keys)."""
    return {
        provider: bool(os.getenv(env_var))
        for provider, env_var in PROVIDER_TO_ENV.items()
    }
