from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging
from dotenv import set_key, unset_key

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_env_paths() -> list:
    """
    Returns a list of ALL .env file paths that should be updated.
    Both root and middleware .env files are kept in sync.
    Priority order: Docker /app/.env, project root .env, middleware local .env
    """
    paths = []
    docker_env = "/app/.env"
    root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    middleware_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

    # In Docker, /app/.env is the single source of truth
    if os.path.exists(docker_env):
        paths.append(docker_env)
    
    # Locally, update both root and middleware .env
    if os.path.exists(root_env):
        paths.append(root_env)
    if middleware_env != root_env and os.path.exists(middleware_env):
        paths.append(middleware_env)
    
    # If no .env found at all, create one at root
    if not paths:
        os.makedirs(os.path.dirname(root_env), exist_ok=True)
        open(root_env, 'a').close()
        paths.append(root_env)
    
    return paths


class KeyUpdate(BaseModel):
    provider: str
    key: str

PROVIDER_TO_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": "OLLAMA_API_KEY",
    "ollama_cloud": "OLLAMA_API_KEY",
    "ollama_local": None,  # Local Ollama has no API key
}

# Minimum key length per provider (rejects obvious fakes like "test" or "123")
MIN_KEY_LENGTHS = {
    "gemini": 20,
    "openai": 20,
    "anthropic": 20,
    "ollama": 1,
    "ollama_cloud": 1,
}


@router.post("/config/keys")
async def update_key(data: KeyUpdate):
    provider = data.provider.lower()
    env_var = PROVIDER_TO_ENV.get(provider)
    
    if provider not in PROVIDER_TO_ENV:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    if env_var is None:
        # ollama_local doesn't use API keys
        raise HTTPException(status_code=400, detail="Local Ollama does not use API keys")

    # Basic validation — reject obviously fake keys
    min_len = MIN_KEY_LENGTHS.get(provider, 10)
    if len(data.key.strip()) < min_len:
        raise HTTPException(
            status_code=400,
            detail=f"API key too short. {provider.capitalize()} keys are typically longer than {min_len} characters."
        )

    clean_key = data.key.strip()

    # Write to ALL .env files for consistency
    env_paths = _get_env_paths()
    for env_path in env_paths:
        try:
            set_key(env_path, env_var, clean_key)
            logger.info(f"API key written to {env_path} for {provider} ({env_var})")
        except Exception as e:
            logger.warning(f"Failed to write key to {env_path}: {e}")

    # Also inject into the running process for immediate use
    os.environ[env_var] = clean_key

    logger.info(f"API key updated for {provider} ({env_var})")
    return {"status": "success", "message": f"{provider.capitalize()} API key saved"}


@router.delete("/config/keys/{provider}")
async def delete_key(provider: str):
    provider = provider.lower()
    env_var = PROVIDER_TO_ENV.get(provider)
    
    if provider not in PROVIDER_TO_ENV:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    if env_var is None:
        return {"status": "success", "message": "Local Ollama has no API key to remove"}

    # Remove from ALL .env files
    env_paths = _get_env_paths()
    for env_path in env_paths:
        try:
            unset_key(env_path, env_var)
            logger.info(f"API key removed from {env_path} for {provider} ({env_var})")
        except Exception as e:
            logger.warning(f"Failed to remove key from {env_path}: {e}")

    # Remove from current running process
    if env_var in os.environ:
        del os.environ[env_var]

    logger.info(f"API key removed for {provider} ({env_var})")
    return {"status": "success", "message": f"{provider.capitalize()} API key removed"}


@router.get("/config/keys/status")
async def key_status():
    """Returns which providers have keys configured (without exposing the keys)."""
    return {
        provider: bool(os.getenv(env_var)) if env_var else False
        for provider, env_var in PROVIDER_TO_ENV.items()
        if provider not in ("ollama",)  # Exclude the legacy 'ollama' alias
    }
