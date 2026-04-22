from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging

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


def _read_env_lines(env_path: str) -> list:
    if not os.path.exists(env_path):
        return []
    with open(env_path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _write_env_lines(env_path: str, lines: list) -> None:
    parent = os.path.dirname(env_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    content = "\n".join(lines)
    if content and not content.endswith("\n"):
        content += "\n"
    with open(env_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _format_env_assignment(env_var: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'{env_var}="{escaped}"'


def _set_env_value(env_path: str, env_var: str, value: str) -> None:
    lines = _read_env_lines(env_path)
    updated = []
    found = False

    for line in lines:
        if line.startswith(f"{env_var}="):
            if not found:
                updated.append(_format_env_assignment(env_var, value))
                found = True
            continue
        updated.append(line)

    if not found:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append(_format_env_assignment(env_var, value))

    _write_env_lines(env_path, updated)


def _unset_env_value(env_path: str, env_var: str) -> None:
    lines = _read_env_lines(env_path)
    updated = [line for line in lines if not line.startswith(f"{env_var}=")]
    _write_env_lines(env_path, updated)


class KeyUpdate(BaseModel):
    provider: str
    key: str
    persist: bool = False

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

    # Also inject into the running process for immediate use
    os.environ[env_var] = clean_key

    if data.persist:
        env_paths = _get_env_paths()
        successful_writes = 0
        for env_path in env_paths:
            try:
                _set_env_value(env_path, env_var, clean_key)
                successful_writes += 1
                logger.info(f"API key written to {env_path} for {provider} ({env_var})")
            except Exception as e:
                logger.warning(f"Failed to write key to {env_path}: {e}")

        if successful_writes == 0:
            raise HTTPException(status_code=500, detail="Failed to persist API key to env files")

        logger.info(f"API key persisted for {provider} ({env_var})")
        return {"status": "success", "message": f"{provider.capitalize()} API key saved"}

    logger.info(f"API key loaded in memory for {provider} ({env_var})")
    return {"status": "success", "message": f"{provider.capitalize()} API key loaded for this session"}


@router.delete("/config/keys/{provider}")
async def delete_key(provider: str):
    provider = provider.lower()
    env_var = PROVIDER_TO_ENV.get(provider)
    
    if provider not in PROVIDER_TO_ENV:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    if env_var is None:
        return {"status": "success", "message": "Local Ollama has no API key to remove"}

    # Remove from all .env files using an in-place update.
    env_paths = _get_env_paths()
    successful_updates = 0
    for env_path in env_paths:
        try:
            _unset_env_value(env_path, env_var)
            successful_updates += 1
            logger.info(f"API key removed from {env_path} for {provider} ({env_var})")
        except Exception as e:
            logger.warning(f"Failed to remove key from {env_path}: {e}")

    if successful_updates == 0:
        raise HTTPException(status_code=500, detail="Failed to update env files")

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
