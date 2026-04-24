import json
import logging
import os
import threading
import urllib.error
import urllib.request

import litellm
import litellm.exceptions


logger = logging.getLogger(__name__)
litellm.suppress_debug_info = True
_LOCAL_PULL_LOCK = threading.Lock()


def _classify_error(e, model_id: str) -> str:
    err_str = str(e)
    err_lower = err_str.lower()

    if isinstance(e, litellm.exceptions.RateLimitError):
        retry_after = getattr(e, "retry_after", None)
        retry_msg = f" Retry after {retry_after}s." if retry_after else ""
        return (
            f"**[RATE LIMIT EXCEEDED - {model_id.upper()}]**\n"
            f"The API rate limit has been reached for this provider.{retry_msg}\n"
            f"Wait a moment and try again, or switch to a different model in Settings."
        )

    if (
        isinstance(e, litellm.exceptions.AuthenticationError)
        or "unauthorized" in err_lower
        or "invalid api key" in err_lower
        or "401" in err_lower
        or "forbidden" in err_lower
    ):
        return (
            f"**[AUTHENTICATION ERROR - {model_id.upper()}]**\n"
            f"The API key for {model_id} is invalid, expired, or missing.\n"
            f"Please update it in Settings > AI Preferences."
        )

    if isinstance(e, litellm.exceptions.BudgetExceededError) or "quota" in err_lower:
        return (
            f"**[QUOTA EXCEEDED - {model_id.upper()}]**\n"
            f"Your API quota or spending limit has been reached for {model_id}.\n"
            f"Check your billing dashboard or upgrade your plan."
        )

    if (
        isinstance(e, litellm.exceptions.APIConnectionError)
        or "connection" in err_lower
        or "network is unreachable" in err_lower
        or "urlopen error" in err_lower
        or "no route to host" in err_lower
        or "timed out" in err_lower
        or "name or service not known" in err_lower
        or "temporary failure in name resolution" in err_lower
    ):
        return (
            f"**[CONNECTION FAILED - {model_id.upper()}]**\n"
            f"Could not reach the AI service. Details: {err_str[:200]}...\n"
            f"Troubleshooting: if this is local Ollama, ensure the container is running. "
            f"If it is a cloud provider, verify your API key and outbound internet access."
        )

    if "model" in err_lower and "not found" in err_lower:
        return (
            f"**[MODEL NOT READY - {model_id.upper()}]**\n"
            f"The selected Ollama model is not installed yet. "
            f"The service will try to download it automatically on first use. "
            f"If this keeps happening, verify the container has internet access."
        )

    if isinstance(e, litellm.exceptions.ContextWindowExceededError):
        return (
            f"**[CONTEXT LIMIT - {model_id.upper()}]**\n"
            f"The request exceeded the model's maximum context window."
        )

    return f"**[ERROR - {model_id.upper()}]**\n{err_str[:300]}"


def _get_local_ollama_base() -> str:
    explicit_base = os.getenv("OLLAMA_API_BASE")
    if explicit_base:
        return explicit_base
    return "http://localhost:11434"


def _get_cloud_ollama_urls() -> tuple[str, str]:
    cloud_url = os.getenv("OLLAMA_CLOUD_URL")
    if cloud_url and cloud_url.strip():
        return cloud_url.strip(), cloud_url.strip()
    return "https://ollama.com", "https://ollama.com"


def _default_local_ollama_model() -> str:
    model = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
    return model or "llama3.2"


def _default_cloud_ollama_model() -> str:
    return "gpt-oss:20b"


def _fetch_ollama_tags(tags_base: str, api_key: str | None = None, timeout: float = 5.0) -> dict:
    req = urllib.request.Request(f"{tags_base.rstrip('/')}/api/tags")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Ollama tags request failed with HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _extract_ollama_model_names(data: dict) -> list[str]:
    names = []
    for model in data.get("models", []):
        name = model.get("name") or model.get("model")
        if name and name not in names:
            names.append(name)
    return names


def _is_ollama_local_reachable() -> str | None:
    base = _get_local_ollama_base()
    bases_to_try = [base]

    if "localhost" in base:
        bases_to_try.extend(["http://127.0.0.1:11434", "http://ollama:11434"])
    elif "127.0.0.1" in base:
        bases_to_try.extend(["http://localhost:11434", "http://ollama:11434"])
    elif "ollama" in base and "com" not in base:
        bases_to_try.extend(["http://localhost:11434", "http://127.0.0.1:11434"])

    checked = set()
    for url in bases_to_try:
        if url in checked:
            continue
        checked.add(url)
        try:
            _fetch_ollama_tags(url, timeout=1.5)
            return url
        except Exception:
            continue
    return None


def _is_ollama_cloud_reachable() -> bool:
    api_key = os.getenv("OLLAMA_API_KEY")
    if not api_key or not api_key.strip() or api_key.lower() == "none":
        return False
    try:
        tags_base, _ = _get_cloud_ollama_urls()
        _fetch_ollama_tags(tags_base, api_key=api_key, timeout=8.0)
        return True
    except Exception:
        return False


def _select_cloud_model(available_names: list[str]) -> str:
    preferred_models = [
        "gpt-oss:20b",
        "gpt-oss:120b",
        "glm-4.7",
        "minimax-m2.1",
        "minimax-m2.5",
        "gemma3:4b",
        "gemma3:12b",
    ]
    for preferred in preferred_models:
        if preferred in available_names:
            return preferred
    return available_names[0] if available_names else _default_cloud_ollama_model()


def _get_local_ollama_state() -> dict:
    configured_model = _default_local_ollama_model()
    base = _is_ollama_local_reachable()
    if not base:
        return {
            "base": None,
            "reachable": False,
            "model": configured_model,
            "available_models": [],
            "ready": False,
            "status_text": "SERVER NOT RUNNING",
        }

    try:
        data = _fetch_ollama_tags(base, timeout=2.0)
        available_names = _extract_ollama_model_names(data)
    except Exception as e:
        logger.warning(f"Failed to fetch local Ollama model list from {base}: {e}")
        available_names = []

    selected_model = configured_model if configured_model in available_names else (available_names[0] if available_names else configured_model)
    ready = bool(available_names)
    status_text = "AVAILABLE - CLICK TO SELECT" if ready else f"FIRST USE DOWNLOADS {selected_model}"

    return {
        "base": base,
        "reachable": True,
        "model": selected_model,
        "available_models": available_names,
        "ready": ready,
        "status_text": status_text,
    }


def _get_cloud_ollama_state() -> dict:
    api_key = os.getenv("OLLAMA_API_KEY")
    if not api_key or not api_key.strip() or api_key.lower() == "none":
        return {
            "configured": False,
            "reachable": False,
            "model": _default_cloud_ollama_model(),
            "status_text": "MISSING API KEY",
        }

    try:
        tags_base, _ = _get_cloud_ollama_urls()
        data = _fetch_ollama_tags(tags_base, api_key=api_key, timeout=8.0)
        available_names = _extract_ollama_model_names(data)
        return {
            "configured": True,
            "reachable": True,
            "model": _select_cloud_model(available_names),
            "status_text": "AVAILABLE - CLICK TO SELECT",
        }
    except Exception as e:
        logger.warning(f"Ollama Cloud reachability check failed: {e}")
        return {
            "configured": True,
            "reachable": False,
            "model": _default_cloud_ollama_model(),
            "status_text": "KEY LOADED - NETWORK OR AUTH ERROR",
        }


def get_ollama_model(tags_base: str, is_cloud: bool = False) -> str:
    try:
        api_key = os.getenv("OLLAMA_API_KEY") if is_cloud else None
        timeout = 8.0 if is_cloud else 2.0
        data = _fetch_ollama_tags(tags_base, api_key=api_key, timeout=timeout)
        available_names = _extract_ollama_model_names(data)
        if not available_names:
            return _default_cloud_ollama_model() if is_cloud else _default_local_ollama_model()
        if is_cloud:
            return _select_cloud_model(available_names)
        configured_model = _default_local_ollama_model()
        return configured_model if configured_model in available_names else available_names[0]
    except Exception as e:
        logger.warning(f"Failed to fetch Ollama model list from {tags_base}: {e}")
        return _default_cloud_ollama_model() if is_cloud else _default_local_ollama_model()


def _strip_ollama_prefix(model_name: str) -> str:
    prefix = "ollama/"
    if model_name.startswith(prefix):
        return model_name[len(prefix):]
    return model_name


def _normalize_ollama_messages(messages: list) -> list:
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


def _pull_local_ollama_model(api_base: str, model_name: str) -> None:
    with _LOCAL_PULL_LOCK:
        try:
            data = _fetch_ollama_tags(api_base, timeout=2.0)
            if model_name in _extract_ollama_model_names(data):
                return
        except Exception:
            pass

        logger.info(f"Pulling missing local Ollama model: {model_name}")
        req = urllib.request.Request(
            f"{api_base.rstrip('/')}/api/pull",
            data=json.dumps({"model": model_name, "stream": False}).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=1800.0) as response:
            detail = json.loads(response.read().decode("utf-8"))
            if response.status != 200:
                raise RuntimeError(f"Ollama Local HTTP {response.status}: {str(detail)[:300]}")
            if detail.get("error"):
                raise RuntimeError(detail["error"])


def _ollama_direct_chat(
    messages: list,
    model_cfg: dict,
    max_tokens: int,
    temperature: float,
    retry_after_pull: bool = False,
) -> str:
    api_base = (model_cfg.get("api_base") or "http://localhost:11434").rstrip("/")
    api_key = model_cfg.get("api_key")
    model_name = _strip_ollama_prefix(model_cfg["model"])
    is_cloud = model_cfg.get("id") == "ollama_cloud"

    if is_cloud and (not api_key or not api_key.strip() or api_key.lower() == "none"):
        raise RuntimeError("Ollama Cloud API key is missing.")

    req = urllib.request.Request(
        f"{api_base}/api/chat",
        data=json.dumps(
            {
                "model": model_name,
                "messages": _normalize_ollama_messages(messages),
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
        ).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    if is_cloud:
        req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=120.0) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        if not is_cloud and not retry_after_pull and e.code == 404 and "not found" in detail.lower():
            _pull_local_ollama_model(api_base, model_name)
            return _ollama_direct_chat(
                messages=messages,
                model_cfg=model_cfg,
                max_tokens=max_tokens,
                temperature=temperature,
                retry_after_pull=True,
            )
        provider_name = "Ollama Cloud" if is_cloud else "Ollama Local"
        raise RuntimeError(f"{provider_name} HTTP {e.code}: {detail[:300]}") from e

    if data.get("error"):
        if not is_cloud and not retry_after_pull and "not found" in str(data["error"]).lower():
            _pull_local_ollama_model(api_base, model_name)
            return _ollama_direct_chat(
                messages=messages,
                model_cfg=model_cfg,
                max_tokens=max_tokens,
                temperature=temperature,
                retry_after_pull=True,
            )
        raise RuntimeError(str(data["error"]))

    content = data.get("message", {}).get("content") or data.get("response")
    if not content:
        raise RuntimeError(f"Ollama returned an empty response: {str(data)[:300]}")
    return content


def get_available_models() -> list:
    from main import reload_env

    reload_env()
    models = []

    local_state = _get_local_ollama_state()
    models.append(
        {
            "id": "ollama_local",
            "name": f"Ollama Local ({local_state['model']})",
            "available": bool(local_state["reachable"]),
            "ready": bool(local_state["ready"]),
            "status_text": local_state["status_text"],
            "type": "device",
        }
    )

    cloud_state = _get_cloud_ollama_state()
    cloud_name = f"Ollama Cloud ({cloud_state['model']})" if cloud_state["configured"] else "Ollama Cloud"
    models.append(
        {
            "id": "ollama_cloud",
            "name": cloud_name,
            "available": bool(cloud_state["reachable"]),
            "configured": bool(cloud_state["configured"]),
            "status_text": cloud_state["status_text"],
            "type": "cloud",
        }
    )

    models.append(
        {
            "id": "gemini",
            "name": "Google Gemini",
            "available": bool(os.getenv("GEMINI_API_KEY")),
            "type": "cloud",
        }
    )
    models.append(
        {
            "id": "openai",
            "name": "OpenAI GPT-4o",
            "available": bool(os.getenv("OPENAI_API_KEY")),
            "type": "cloud",
        }
    )
    models.append(
        {
            "id": "anthropic",
            "name": "Anthropic Claude",
            "available": bool(os.getenv("ANTHROPIC_API_KEY")),
            "type": "cloud",
        }
    )

    return models


def _build_models_to_try(preference: str = None) -> list:
    def _ollama_local_cfg(api_base=None):
        base = api_base or _get_local_ollama_base()
        return {
            "id": "ollama_local",
            "model": f"ollama/{get_ollama_model(base)}",
            "api_base": base,
            "api_key": "ollama",
        }

    def _ollama_cloud_cfg():
        tags_base, api_base = _get_cloud_ollama_urls()
        return {
            "id": "ollama_cloud",
            "model": f"ollama/{get_ollama_model(tags_base, is_cloud=True)}",
            "api_base": api_base,
            "api_key": os.getenv("OLLAMA_API_KEY"),
        }

    def _gemini_cfg():
        return {"id": "gemini", "model": "gemini/gemini-2.0-flash", "api_key": os.getenv("GEMINI_API_KEY")}

    def _openai_cfg():
        return {"id": "openai", "model": "gpt-4o-mini", "api_key": os.getenv("OPENAI_API_KEY")}

    def _anthropic_cfg():
        return {
            "id": "anthropic",
            "model": "anthropic/claude-3-5-sonnet-20241022",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        }

    if preference:
        if preference in ("ollama_local", "ollama"):
            local_state = _get_local_ollama_state()
            if local_state["reachable"]:
                return [_ollama_local_cfg(local_state["base"])]
            logger.warning("Local Ollama selected but not reachable.")
            return []

        if preference == "ollama_cloud":
            api_key = os.getenv("OLLAMA_API_KEY")
            if api_key and api_key.strip() and api_key.lower() != "none":
                return [_ollama_cloud_cfg()]
            logger.warning("Ollama Cloud selected but no API key configured.")
            return []

        builders = {
            "gemini": _gemini_cfg,
            "openai": _openai_cfg,
            "anthropic": _anthropic_cfg,
        }
        builder = builders.get(preference)
        if builder:
            cfg = builder()
            if cfg.get("api_key"):
                return [cfg]
            logger.warning(f"Model '{preference}' selected but no API key found.")
        else:
            logger.warning(f"Unknown model preference '{preference}'")
        return []

    models = []
    local_state = _get_local_ollama_state()
    if local_state["reachable"]:
        models.append(_ollama_local_cfg(local_state["base"]))

    ollama_key = os.getenv("OLLAMA_API_KEY")
    if ollama_key and ollama_key.strip() and ollama_key.lower() != "none":
        models.append(_ollama_cloud_cfg())

    return models


def get_severity(score: float, anomaly_count: int, total: int) -> str:
    ratio = anomaly_count / total if total > 0 else 0
    if score > 0.8 or ratio > 0.3:
        return "CRITICAL"
    if score > 0.5 or ratio > 0.15:
        return "HIGH"
    if score > 0.2 or ratio > 0.05:
        return "MEDIUM"
    return "LOW"


def generate_incident_report(
    channel: str,
    score: float,
    anomaly_count: int,
    total_windows: int,
    threshold: float,
    device: str,
    model_preference: str = None,
) -> str:
    severity = get_severity(score, anomaly_count, total_windows)
    ratio = round((anomaly_count / total_windows) * 100, 2) if total_windows > 0 else 0
    models_to_try = _build_models_to_try(model_preference)

    if not models_to_try:
        logger.info("No AI models available - returning static incident summary.")
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
            if model_cfg["id"] == "ollama_local":
                logger.info(f"Using OLLAMA LOCAL endpoint: {model_cfg.get('api_base')}")
            elif model_cfg["id"] == "ollama_cloud":
                logger.info(f"Using OLLAMA CLOUD endpoint: {model_cfg.get('api_base')}")
            else:
                logger.info(f"Generating report with {model_name}")

            if model_cfg["id"] in ("ollama_local", "ollama_cloud"):
                return _ollama_direct_chat(
                    messages=[{"role": "user", "content": prompt}],
                    model_cfg=model_cfg,
                    max_tokens=300,
                    temperature=0.7,
                )

            kwargs = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.7,
            }
            if model_cfg.get("api_key"):
                kwargs["api_key"] = model_cfg["api_key"]
            response = litellm.completion(**kwargs)
            return response.choices[0].message.content

        except (litellm.exceptions.RateLimitError, litellm.exceptions.BudgetExceededError) as e:
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
    from main import reload_env

    reload_env()
    models_to_try = _build_models_to_try(model_preference)

    if not models_to_try:
        return (
            "**[AI SERVICE UNAVAILABLE]**\n\n"
            "No AI models are currently reachable. Please ensure Ollama is running locally "
            "or configure valid cloud API keys in the settings menu."
        )

    last_error_msg = None
    for model_cfg in models_to_try:
        try:
            model_name = model_cfg["model"]
            if model_cfg["id"] == "ollama_local":
                logger.info(f"Chat using OLLAMA LOCAL endpoint: {model_cfg.get('api_base')}")
            elif model_cfg["id"] == "ollama_cloud":
                logger.info(f"Chat using OLLAMA CLOUD endpoint: {model_cfg.get('api_base')}")
            else:
                logger.info(f"Chat using {model_name}")

            if model_cfg["id"] in ("ollama_local", "ollama_cloud"):
                return _ollama_direct_chat(
                    messages=messages,
                    model_cfg=model_cfg,
                    max_tokens=500,
                    temperature=0.7,
                )

            kwargs = {
                "model": model_name,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
            }
            if model_cfg.get("api_key"):
                kwargs["api_key"] = model_cfg["api_key"]
            response = litellm.completion(**kwargs)
            return response.choices[0].message.content

        except (litellm.exceptions.RateLimitError, litellm.exceptions.BudgetExceededError) as e:
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

    return last_error_msg or (
        "**[AI SERVICE UNAVAILABLE]**\n\n"
        "No AI models are currently reachable. Please ensure Ollama is running locally "
        "or configure valid cloud API keys in Settings."
    )
