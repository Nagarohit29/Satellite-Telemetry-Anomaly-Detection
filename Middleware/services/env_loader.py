import os
from dotenv import load_dotenv

def reload_env(path=None):
    """Dynamically reload environment variables from the project env files, preserving non-empty in-memory keys."""
    keys_to_preserve = [
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OLLAMA_API_KEY",
        "N2YO_API_KEY",
        "OLLAMA_API_BASE",
        "OLLAMA_MODEL"
    ]
    preserved = {k: os.environ[k] for k in keys_to_preserve if k in os.environ and os.environ[k]}

    config_env = "/app/config/.env"
    
    # Calculate paths relative to this service file (which is in Middleware/services/env_loader.py)
    # We want project root (../../.env) and Middleware root (../.env)
    services_dir = os.path.dirname(os.path.abspath(__file__))
    middleware_dir = os.path.dirname(services_dir)
    project_dir = os.path.dirname(middleware_dir)
    
    root_env = os.path.join(project_dir, '.env')
    middleware_env = os.path.join(middleware_dir, '.env')
    
    # Load in order so more specific files can override defaults.
    targets = [target for target in [path, config_env, root_env, middleware_env] if target]
    loaded = set()
    for target in targets:
        if target in loaded:
            continue
        if os.path.exists(target):
            load_dotenv(target, override=False)
            loaded.add(target)
    load_dotenv()

    # Restore preserved in-memory keys
    for k, v in preserved.items():
        os.environ[k] = v
