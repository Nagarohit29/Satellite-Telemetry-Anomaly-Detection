import os
import litellm
import litellm.exceptions
import logging
import urllib.request
import json

logger = logging.getLogger(__name__)

# Suppress litellm's verbose output
litellm.suppress_debug_info = True


def _classify_error(e, model_id: str) -> str:
    """Extract a real, actionable error message from litellm exceptions."""
    err_str = str(e)

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
    if isinstance(e, litellm.exceptions.AuthenticationError):
        return (
            f"**[AUTHENTICATION ERROR — {model_id.upper()}]**\n"
            f"The API key for {model_id} is invalid or has been revoked.\n"
            f"Please update your key in Settings > AI Preferences."
        )

    # ── Budget / Quota Exceeded ──
    if isinstance(e, litellm.exceptions.BudgetExceededError) or '429' in err_str or 'quota' in err_str.lower():
        return (
            f"**[QUOTA EXCEEDED — {model_id.upper()}]**\n"
            f"Your API quota or spending limit has been reached for {model_id}.\n"
            f"Check your billing dashboard or upgrade your plan."
        )

    # ── Connection errors ──
    if isinstance(e, litellm.exceptions.APIConnectionError):
        return (
            f"**[CONNECTION FAILED — {model_id.upper()}]**\n"
            f"Could not connect to {model_id}. The service may be down or unreachable."
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


def _get_ollama_urls() -> tuple:
    """
    Returns (tags_base, litellm_base) for Ollama.

    - tags_base:   used for /api/tags model listing (e.g. https://ollama.com or http://127.0.0.1:11434)
    - litellm_base: used as api_base for litellm.completion (e.g. https://api.ollama.com or http://127.0.0.1:11434)

    If OLLAMA_API_BASE is explicitly set, both URLs use that value.
    Otherwise: if an OLLAMA_API_KEY is present → cloud endpoints; else → localhost.
    """
    explicit_base = os.getenv("OLLAMA_API_BASE")
    if explicit_base:
        return explicit_base, explicit_base

    api_key = os.getenv("OLLAMA_API_KEY")
    if api_key:
        # Ollama Cloud: /api/tags lives at ollama.com, litellm uses api.ollama.com
        return "https://ollama.com", "https://api.ollama.com"

    # Local Ollama
    return "http://127.0.0.1:11434", "http://127.0.0.1:11434"


def _is_ollama_reachable(tags_base: str) -> bool:
    """Quick connectivity check — returns True if Ollama (or the cloud proxy) is listening."""
    try:
        req = urllib.request.Request(f"{tags_base}/api/tags")
        api_key = os.getenv("OLLAMA_API_KEY")
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")

        # Cloud endpoints can be slower; use 3s for them, 1s for local
        timeout = 3.0 if "ollama.com" in tags_base else 1.0
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_ollama_model(tags_base: str) -> str:
    """Dynamically fetch a suitable model from Ollama.

    For cloud endpoints the model list is sorted by popularity, which often
    puts huge (671B / 1T) models first.  These routinely return 500 errors
    on the shared cloud infra.  We therefore prefer small, proven models.
    """
    env_model = os.getenv("OLLAMA_MODEL")
    if env_model:
        return env_model

    # Models known to work reliably on Ollama Cloud, in preference order.
    PREFERRED_MODELS = [
        "gemma3:4b", "ministral-3:8b", "ministral-3:3b",
        "gemma3:12b", "llama3", "llama3:8b", "gemma3:27b",
    ]

    try:
        req = urllib.request.Request(f"{tags_base}/api/tags")
        api_key = os.getenv("OLLAMA_API_KEY")
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")

        timeout = 3.0 if "ollama.com" in tags_base else 1.0
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode())
            if "models" not in data or len(data["models"]) == 0:
                return "llama3"

            available_names = {m.get("name") for m in data["models"]}

            # For local Ollama, just use the first model (user controls what's pulled)
            if "ollama.com" not in tags_base:
                return data["models"][0].get("name", "llama3")

            # For cloud: pick the first preferred model that exists in the catalog
            for preferred in PREFERRED_MODELS:
                if preferred in available_names:
                    logger.info(f"Selected cloud model: {preferred}")
                    return preferred

            # Fallback: pick the first model under 100B params (by name heuristic)
            for m in data["models"]:
                name = m.get("name", "")
                # Skip models with size hints suggesting >100B
                if any(tag in name for tag in [":671b", ":1t", ":480b", ":235b", ":120b"]):
                    continue
                return name

            # Ultimate fallback
            return data["models"][0].get("name", "llama3")
    except Exception:
        pass
    return "llama3"



def get_available_models() -> list:
    """Returns a list of available AI models and their status."""
    models = []

    tags_base, _ = _get_ollama_urls()
    api_key = os.getenv("OLLAMA_API_KEY")

    has_ollama = _is_ollama_reachable(tags_base)

    ollama_model = get_ollama_model(tags_base) if has_ollama else "llama3"
    models.append({
        "id": "ollama",
        "name": f"Ollama ({ollama_model})",
        "available": has_ollama
    })

    models.append({
        "id": "gemini",
        "name": "Google Gemini",
        "available": bool(os.getenv("GEMINI_API_KEY"))
    })

    models.append({
        "id": "openai",
        "name": "OpenAI GPT-4o",
        "available": bool(os.getenv("OPENAI_API_KEY"))
    })

    models.append({
        "id": "anthropic",
        "name": "Anthropic Claude",
        "available": bool(os.getenv("ANTHROPIC_API_KEY"))
    })

    return models


def _build_models_to_try(preference: str = None) -> list:
    """
    Build an ordered list of model configs to attempt.
    """
    tags_base, litellm_base = _get_ollama_urls()

    # ── helper to build per-provider configs ──
    def _ollama_cfg():
        cfg = {
            "id": "ollama",
            "model": f"ollama/{get_ollama_model(tags_base)}",
            "api_base": litellm_base,
        }
        api_key = os.getenv("OLLAMA_API_KEY")
        if api_key:
            cfg["api_key"] = api_key
        return cfg

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
        cfgs = {
            "ollama": _ollama_cfg,
            "gemini": _gemini_cfg,
            "openai": _openai_cfg,
            "anthropic": _anthropic_cfg,
        }
        builder = cfgs.get(preference)
        if builder:
            cfg = builder()
            # Pre-flight: skip cloud models if API key is missing
            if preference != "ollama" and not cfg.get("api_key"):
                logger.info(f"Skipping {preference}: no API key configured.")
                return []  # Empty list → caller will return static fallback
            # Pre-flight: skip ollama if not reachable
            if preference == "ollama" and not _is_ollama_reachable(tags_base):
                logger.info("Skipping ollama: server not reachable. Falling back to auto-discovery.")
                # If selected model is down, don't just fail — fall through to auto-discovery
                # to find any other working model.
            else:
                return [cfg]
        # Unknown preference → fall through to auto
        logger.warning(f"Unknown model preference '{preference}', falling back to auto")

    # ── auto-discover: only include models that have credentials/connectivity ──
    models = []
    if _is_ollama_reachable(tags_base):
        models.append(_ollama_cfg())

    if os.getenv("GEMINI_API_KEY"):
        models.append(_gemini_cfg())
    if os.getenv("OPENAI_API_KEY"):
        models.append(_openai_cfg())
    if os.getenv("ANTHROPIC_API_KEY"):
        models.append(_anthropic_cfg())

    return models


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


def chat_with_llm(messages: list, model_preference: str = None) -> str:
    """Handle multi-turn conversations with the LLM."""
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

            logger.info(f"Chat attempt using {model_name}")

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