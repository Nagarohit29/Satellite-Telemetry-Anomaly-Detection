import os
import litellm
import litellm.exceptions
import logging
import urllib.error
import urllib.request
import json

logger = logging.getLogger(__name__)

# Suppress litellm's verbose output
litellm.suppress_debug_info = True


def _classify_error(e, model_id: str) -> str:
    """Extract a real, actionable error message from litellm exceptions."""
    err_str = str(e)
    err_lower = err_str.lower()

    # ── Rate Limit (429) ──
    if isinstance(e, litellm.exceptions.RateLimitError):
        # Try to extract retry-after from the error
        retry_after = getattr(e, 'retry_after', None)
        retry_msg = f" Retry after {retry_after}s." if retry_after else ""
        return (
            f"**[RATE LIMIT EXCEEDED — {model_id.upper()}]**\n"
            f"The API rate limit has been reached for this provider.{retry_msg}\n"
            f"This typically means you've sent too many requests in a short period. "
            f"Wait a moment and try again, or switch to a different model in Settings."
        )

    # ── Authentication (401 / invalid key) ──
    if (
        isinstance(e, litellm.exceptions.AuthenticationError)
        or "unauthorized" in err_lower
        or "invalid api key" in err_lower
        or "401" in err_lower
    ):
        return (
            f"**[AUTHENTICATION ERROR — {model_id.upper()}]**\n"
            f"The API key for {model_id} is invalid or has been revoked.\n"
            f"Please update your key in Settings > AI Preferences."
        )

    # ── Budget / Quota Exceeded ──
    if isinstance(e, litellm.exceptions.BudgetExceededError) or '429' in err_str or 'quota' in err_lower:
        return (
            f"**[QUOTA EXCEEDED — {model_id.upper()}]**\n"
            f"Your API quota or spending limit has been reached for {model_id}.\n"
            f"Check your billing dashboard or upgrade your plan."
        )

    # ── Connection errors ──
    if isinstance(e, litellm.exceptions.APIConnectionError) or "connection" in err_lower:
        return (
            f"**[CONNECTION FAILED — {model_id.upper()}]**\n"
            f"Could not reach the AI service. Details: {err_str[:200]}...\n"
            f"Troubleshooting: If this is local Ollama, ensure it is running in Docker. "
            f"If it is a cloud provider, check your API key and URL."
        )

    # ── Context length ──
    if isinstance(e, litellm.exceptions.ContextWindowExceededError):
        return (
            f"**[CONTEXT LIMIT — {model_id.upper()}]**\n"
            f"The request exceeded the model's maximum context window."
        )

    # ── Generic fallback ──
    return (
        f"**[ERROR — {model_id.upper()}]**\n"
        f"{err_str[:300]}"
    )


# ─────────────────────────────────────────────────────────
# Ollama helpers
# ─────────────────────────────────────────────────────────

def _get_local_ollama_base() -> str:
    """Returns the base URL for local/Docker Ollama."""
    explicit_base = os.getenv("OLLAMA_API_BASE")
    if explicit_base:
        return explicit_base
    return "http://localhost:11434"


def _get_cloud_ollama_urls() -> tuple:
    """Returns (tags_base, api_base) for Ollama Cloud."""
    return "https://ollama.com", "https://ollama.com"


def _is_ollama_local_reachable() -> str:
    """Check if local/Docker Ollama is reachable. Returns working URL or None."""
    base = _get_local_ollama_base()
    bases_to_try = [base]

    if "localhost" in base:
        bases_to_try.extend(["http://127.0.0.1:11434", "http://ollama:11434"])
    elif "127.0.0.1" in base:
        bases_to_try.extend(["http://localhost:11434", "http://ollama:11434"])
    elif "ollama" in base and "com" not in base:
        bases_to_try.extend(["http://localhost:11434", "http://127.0.0.1:11434"])

    for url in bases_to_try:
        try:
            req = urllib.request.Request(f"{url}/api/tags")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return None


def _is_ollama_cloud_reachable() -> bool:
    """Check if Ollama Cloud is reachable with the API key."""
    api_key = os.getenv("OLLAMA_API_KEY")
    if not api_key or not api_key.strip() or api_key.lower() == "none":
        return False
    try:
        req = urllib.request.Request("https://ollama.com/api/tags")
        req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_ollama_model(tags_base: str, is_cloud: bool = False) -> str:
    """Dynamically fetch a suitable model from Ollama.

    For LOCAL: uses OLLAMA_MODEL env var, or picks the first pulled model.
    For CLOUD: ignores OLLAMA_MODEL (it's for local only), and picks from
    the cloud catalog preferring small, proven models.
    """
    # OLLAMA_MODEL env var only applies to LOCAL Ollama
    if not is_cloud:
        env_model = os.getenv("OLLAMA_MODEL")
        if env_model:
            return env_model

    # Models known to work reliably on Ollama Cloud, in preference order.
    PREFERRED_CLOUD_MODELS = [
        "gemma3:4b", "ministral-3:8b", "gemma3:12b",
        "ministral-3:14b", "devstral-small-2:24b",
        "minimax-m2.1", "minimax-m2.5", "glm-4.7",
    ]

    try:
        req = urllib.request.Request(f"{tags_base}/api/tags")
        api_key = os.getenv("OLLAMA_API_KEY")
        if api_key and "ollama.com" in tags_base:
            req.add_header("Authorization", f"Bearer {api_key}")

        timeout = 5.0 if "ollama.com" in tags_base else 1.0
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode())
            if "models" not in data or len(data["models"]) == 0:
                return "gemma3:4b" if is_cloud else "llama3"

            available_names = {m.get("name") for m in data["models"]}

            # For local Ollama, just use the first model (user controls what's pulled)
            if not is_cloud:
                return data["models"][0].get("name", "llama3")

            # For cloud: pick the first preferred model that exists in the catalog
            for preferred in PREFERRED_CLOUD_MODELS:
                if preferred in available_names:
                    logger.info(f"Selected cloud model: {preferred}")
                    return preferred

            # Fallback: pick the first model under 100B params (by name heuristic)
            for m in data["models"]:
                name = m.get("name", "")
                if any(tag in name for tag in [":671b", ":1t", ":480b", ":235b", ":120b", ":123b"]):
                    continue
                return name

            # Ultimate fallback
            return data["models"][0].get("name", "gemma3:4b")
    except Exception as e:
        logger.warning(f"Failed to fetch Ollama model list from {tags_base}: {e}")
    return "gemma3:4b" if is_cloud else "llama3"


def _strip_ollama_prefix(model_name: str) -> str:
    """Return the native Ollama model name from a LiteLLM-style model id."""
    prefix = "ollama/"
    if model_name.startswith(prefix):
        return model_name[len(prefix):]
    return model_name


def _normalize_ollama_cloud_messages(messages: list) -> list:
    """Make chat history compatible with Ollama Cloud's strict role ordering."""
    system_parts = []
    normalized = []

    for raw_message in messages:
        role = (raw_message.get("role") or "user").lower()
        content = str(raw_message.get("content") or "").strip()
        if not content:
            continue

        if role == "system":
            system_parts.append(content)
            continue

        if role not in ("user", "assistant"):
            role = "user"

        # The UI has a canned assistant greeting before the first user message.
        # Ollama Cloud rejects histories that start with assistant.
        if not normalized and role == "assistant":
            continue

        if normalized and normalized[-1]["role"] == role:
            normalized[-1]["content"] = f"{normalized[-1]['content']}\n\n{content}"
            continue

        normalized.append({"role": role, "content": content})

    if not normalized:
        normalized.append({"role": "user", "content": "Hello."})

    if normalized[0]["role"] != "user":
        normalized.insert(0, {"role": "user", "content": "Continue the conversation."})

    if system_parts:
        instructions = "\n\n".join(system_parts)
        normalized[0]["content"] = f"{instructions}\n\n{normalized[0]['content']}"

    return normalized


def _ollama_direct_chat(
    messages: list,
    model_cfg: dict,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Ollama's native HTTP API for Ollama Cloud."""
    api_base = (model_cfg.get("api_base") or "https://ollama.com").rstrip("/")
    api_key = model_cfg.get("api_key")
    model_name = _strip_ollama_prefix(model_cfg["model"])

    if not api_key or not api_key.strip() or api_key.lower() == "none":
        raise RuntimeError("Ollama Cloud API key is missing.")

    payload = {
        "model": model_name,
        "messages": _normalize_ollama_cloud_messages(messages),
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    req = urllib.request.Request(
        f"{api_base}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120.0) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama Cloud HTTP {e.code}: {detail[:300]}") from e

    content = data.get("message", {}).get("content") or data.get("response")
    if not content:
        raise RuntimeError(f"Ollama Cloud returned an empty response: {str(data)[:300]}")
    return content


# ─────────────────────────────────────────────────────────
# Model listing for the UI
# ─────────────────────────────────────────────────────────

def get_available_models() -> list:
    """Returns a list of available AI models and their status.
    
    Ollama Local and Ollama Cloud are listed as SEPARATE entries.
    Models without API keys are marked as unavailable.
    """
    # Force refresh environment variables to pick up keys saved in Web UI
    from main import reload_env
    reload_env()

    models = []

    # ── 1. Ollama Local (always shown — available if server reachable) ──
    local_base = _get_local_ollama_base()
    working_local = _is_ollama_local_reachable()
    local_model_name = get_ollama_model(working_local if working_local else local_base)
    models.append({
        "id": "ollama_local",
        "name": f"Ollama Local ({local_model_name})",
        "available": bool(working_local),
        "type": "device",  # UI hint: this is a local/device model
    })

    # ── 2. Ollama Cloud (ALWAYS shown — like other cloud models) ──
    has_ollama_key = bool(os.getenv("OLLAMA_API_KEY"))
    if has_ollama_key:
        cloud_tags_base, _ = _get_cloud_ollama_urls()
        cloud_model_name = get_ollama_model(cloud_tags_base, is_cloud=True)
        cloud_name = f"Ollama Cloud ({cloud_model_name})"
    else:
        cloud_name = "Ollama Cloud"
    models.append({
        "id": "ollama_cloud",
        "name": cloud_name,
        "available": has_ollama_key,
        "type": "cloud",
    })

    # ── 3. Cloud API models (available only when keys are present) ──
    models.append({
        "id": "gemini",
        "name": "Google Gemini",
        "available": bool(os.getenv("GEMINI_API_KEY")),
        "type": "cloud",
    })

    models.append({
        "id": "openai",
        "name": "OpenAI GPT-4o",
        "available": bool(os.getenv("OPENAI_API_KEY")),
        "type": "cloud",
    })

    models.append({
        "id": "anthropic",
        "name": "Anthropic Claude",
        "available": bool(os.getenv("ANTHROPIC_API_KEY")),
        "type": "cloud",
    })

    return models


# ─────────────────────────────────────────────────────────
# Model selection / fallback logic
# ─────────────────────────────────────────────────────────

def _build_models_to_try(preference: str = None) -> list:
    """
    Build an ordered list of model configs to attempt.
    
    Rules:
    1. If user explicitly selected a model, try ONLY that model (no silent fallback to others).
    2. If no model selected (Auto Fallback), try: Local Ollama > Cloud APIs with keys.
    3. Cloud API models are NEVER auto-selected — only used when explicitly chosen.
    """

    # ── helper to build per-provider configs ──
    def _ollama_local_cfg(api_base=None):
        base = api_base or _get_local_ollama_base()
        return {
            "id": "ollama_local",
            "model": f"ollama/{get_ollama_model(base)}",
            "api_base": base,
            "api_key": "ollama",  # Dummy key for litellm compatibility
        }

    def _ollama_cloud_cfg():
        _, litellm_base = _get_cloud_ollama_urls()
        cloud_tags_base, _ = _get_cloud_ollama_urls()
        api_key = os.getenv("OLLAMA_API_KEY")
        return {
            "id": "ollama_cloud",
            "model": f"ollama/{get_ollama_model(cloud_tags_base, is_cloud=True)}",
            "api_base": litellm_base,
            "api_key": api_key,
        }

    def _gemini_cfg():
        return {
            "id": "gemini",
            "model": "gemini/gemini-2.0-flash",
            "api_key": os.getenv("GEMINI_API_KEY"),
        }

    def _openai_cfg():
        return {
            "id": "openai",
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }

    def _anthropic_cfg():
        return {
            "id": "anthropic",
            "model": "anthropic/claude-3-5-sonnet-20241022",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        }

    # ── user explicitly chose a model ──
    if preference:
        builders = {
            "ollama_local": None,  # special handling below
            "ollama_cloud": _ollama_cloud_cfg,
            "gemini": _gemini_cfg,
            "openai": _openai_cfg,
            "anthropic": _anthropic_cfg,
            # Legacy ID compatibility
            "ollama": None,
        }

        if preference in ("ollama_local", "ollama"):
            # User wants local Ollama specifically
            working_base = _is_ollama_local_reachable()
            if working_base:
                return [_ollama_local_cfg(working_base)]
            logger.warning(f"Local Ollama not reachable. No fallback — user explicitly chose it.")
            return []  # Don't silently fall through to cloud APIs

        if preference == "ollama_cloud":
            api_key = os.getenv("OLLAMA_API_KEY")
            if api_key and api_key.strip() and api_key.lower() != "none":
                return [_ollama_cloud_cfg()]
            logger.warning("Ollama Cloud selected but no API key configured.")
            return []

        builder = builders.get(preference)
        if builder:
            cfg = builder()
            if cfg.get("api_key"):
                return [cfg]
            logger.warning(f"Model '{preference}' selected but no API key found.")
            return []
        else:
            logger.warning(f"Unknown model preference '{preference}'")
            return []

    # ── Auto Fallback (no model selected) ──
    # Priority: Local Ollama ONLY. Cloud APIs are NOT auto-selected.
    # User must explicitly choose cloud models in settings.
    models = []

    working_base = _is_ollama_local_reachable()
    if working_base:
        models.append(_ollama_local_cfg(working_base))

    # Also include Ollama Cloud if key is present (it's free-tier, reasonable as fallback)
    ollama_key = os.getenv("OLLAMA_API_KEY")
    if ollama_key and ollama_key.strip() and ollama_key.lower() != "none":
        models.append(_ollama_cloud_cfg())

    return models


# ─────────────────────────────────────────────────────────
# Severity helper
# ─────────────────────────────────────────────────────────

def get_severity(score: float, anomaly_count: int, total: int) -> str:
    ratio = anomaly_count / total if total > 0 else 0
    if score > 0.8 or ratio > 0.3:
        return "CRITICAL"
    elif score > 0.5 or ratio > 0.15:
        return "HIGH"
    elif score > 0.2 or ratio > 0.05:
        return "MEDIUM"
    else:
        return "LOW"


# ─────────────────────────────────────────────────────────
# Incident report generation
# ─────────────────────────────────────────────────────────

def generate_incident_report(
    channel: str,
    score: float,
    anomaly_count: int,
    total_windows: int,
    threshold: float,
    device: str,
    model_preference: str = None
) -> str:
    severity = get_severity(score, anomaly_count, total_windows)
    ratio = round((anomaly_count / total_windows) * 100, 2) if total_windows > 0 else 0

    models_to_try = _build_models_to_try(model_preference)

    # If there are no reachable models at all, skip the LLM call entirely
    if not models_to_try:
        logger.info("No AI models available — returning static incident summary.")
        return (
            f"**[AI OFFLINE]**\n"
            f"Incident Summary: Channel {channel} | Severity: {severity}\n"
            f"Anomaly detected with score {score:.4f} (Threshold: {threshold}). "
            f"{anomaly_count}/{total_windows} windows anomalous ({ratio}%). "
            f"Recommend immediate manual review of subsystem telemetry."
        )

    prompt = f"""You are a spacecraft telemetry analyst AI.
Analyze the following anomaly detection result and generate a concise incident report.

Channel: {channel}
Severity: {severity}
Max Anomaly Score: {score:.4f}
Detection Threshold: {threshold}
Anomalous Windows: {anomaly_count} out of {total_windows} ({ratio}%)
Inference Device: {device}

Write a 3-4 sentence incident report that includes:
1. What was detected and on which channel
2. The severity and what it implies for the spacecraft subsystem
3. A recommended action for the operations team

Keep it professional and concise like a real operations report."""

    last_error_msg = None
    for model_cfg in models_to_try:
        try:
            model_name = model_cfg["model"]
            api_base = model_cfg.get("api_base")
            api_key = model_cfg.get("api_key")

            # Explicit logging for verification
            if model_cfg["id"] == "ollama_local":
                logger.info(f"Using OLLAMA LOCAL endpoint: {api_base}")
            elif model_cfg["id"] == "ollama_cloud":
                logger.info(f"Using OLLAMA CLOUD endpoint: {api_base}")
            else:
                logger.info(f"Generating report with {model_name}")

            kwargs = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.7,
            }
            if api_base:
                kwargs["api_base"] = api_base
            if api_key:
                kwargs["api_key"] = api_key

            if model_cfg["id"] == "ollama_cloud":
                return _ollama_direct_chat(
                    messages=kwargs["messages"],
                    model_cfg=model_cfg,
                    max_tokens=kwargs["max_tokens"],
                    temperature=kwargs["temperature"],
                )

            response = litellm.completion(**kwargs)
            return response.choices[0].message.content

        except (litellm.exceptions.RateLimitError, litellm.exceptions.BudgetExceededError) as e:
            # Rate limit / quota — surface immediately, don't silently fall through
            logger.warning(f"Rate limit hit ({model_cfg['model']}): {e}")
            return _classify_error(e, model_cfg["id"])

        except litellm.exceptions.AuthenticationError as e:
            logger.warning(f"Auth error ({model_cfg['model']}): {e}")
            last_error_msg = _classify_error(e, model_cfg["id"])
            continue

        except Exception as e:
            logger.warning(f"Report generation failed ({model_cfg['model']}): {e}")
            last_error_msg = _classify_error(e, model_cfg["id"])
            continue

    # All attempted models failed — return the last meaningful error
    if last_error_msg:
        return (
            f"{last_error_msg}\n\n"
            f"Incident Summary: Channel {channel} | Severity: {severity}\n"
            f"Score {score:.4f} exceeded threshold {threshold}. "
            f"{anomaly_count}/{total_windows} windows anomalous ({ratio}%)."
        )

    return (
        f"**[AI OFFLINE]**\n"
        f"Incident Summary: Channel {channel} | Severity: {severity}\n"
        f"Anomaly detected with score {score:.4f} (Threshold: {threshold}). "
        f"Recommend immediate manual review of subsystem telemetry."
    )


# ─────────────────────────────────────────────────────────
# Chat
# ─────────────────────────────────────────────────────────

def chat_with_llm(messages: list, model_preference: str = None) -> str:
    """Handle multi-turn conversations"""
    # Force refresh environment variables
    from main import reload_env
    reload_env()

    models_to_try = _build_models_to_try(model_preference)

    if not models_to_try:
        return (
            "**[AI SERVICE UNAVAILABLE]**\n\n"
            "No AI models are currently reachable. Please ensure Ollama is running locally "
            "or configure valid Cloud API keys (Gemini / OpenAI / Claude) in the settings menu."
        )

    last_error_msg = None
    for model_cfg in models_to_try:
        try:
            model_name = model_cfg["model"]
            api_base = model_cfg.get("api_base")
            api_key = model_cfg.get("api_key")

            # Explicit logging for verification
            if model_cfg["id"] == "ollama_local":
                logger.info(f"Chat using OLLAMA LOCAL endpoint: {api_base}")
            elif model_cfg["id"] == "ollama_cloud":
                logger.info(f"Chat using OLLAMA CLOUD endpoint: {api_base}")
            else:
                logger.info(f"Chat using {model_name}")

            kwargs = {
                "model": model_name,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
            }
            if api_base:
                kwargs["api_base"] = api_base
            if api_key:
                kwargs["api_key"] = api_key

            if model_cfg["id"] == "ollama_cloud":
                return _ollama_direct_chat(
                    messages=messages,
                    model_cfg=model_cfg,
                    max_tokens=kwargs["max_tokens"],
                    temperature=kwargs["temperature"],
                )

            response = litellm.completion(**kwargs)
            return response.choices[0].message.content

        except (litellm.exceptions.RateLimitError, litellm.exceptions.BudgetExceededError) as e:
            # Rate limit / quota — surface immediately with real details
            logger.warning(f"Rate limit hit ({model_cfg['model']}): {e}")
            return _classify_error(e, model_cfg["id"])

        except litellm.exceptions.AuthenticationError as e:
            logger.warning(f"Auth error ({model_cfg['model']}): {e}")
            last_error_msg = _classify_error(e, model_cfg["id"])
            continue

        except Exception as e:
            logger.warning(f"Chat failed ({model_cfg['model']}): {e}")
            last_error_msg = _classify_error(e, model_cfg["id"])
            continue

    # Return the last real error message if we have one
    return last_error_msg or (
        "**[AI SERVICE UNAVAILABLE]**\n\n"
        "No AI models are currently reachable. Please ensure Ollama is running locally "
        "or configure valid Cloud API keys in Settings."
    )
