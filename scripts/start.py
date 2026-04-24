import atexit
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request


APP_ROOT = Path("/app")
CONFIG_DIR = APP_ROOT / "config"
ENV_FILE = CONFIG_DIR / ".env"
OLLAMA_HEALTH_URL = "http://127.0.0.1:11434/api/tags"
BACKEND_HEALTH_URL = "http://127.0.0.1:8001/health"
PROCESSES = []


def log(message: str) -> None:
    print(message, flush=True)


def ensure_env_files() -> None:
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
    if not ENV_FILE.exists():
        ENV_FILE.write_text(
            "\n".join(
                [
                    "ANTHROPIC_API_KEY=",
                    "GEMINI_API_KEY=",
                    "OPENAI_API_KEY=",
                    "OLLAMA_API_BASE=http://127.0.0.1:11434",
                    "OLLAMA_MODEL=llama3.2",
                    "OLLAMA_PREFETCH_MODEL=true",
                    "OLLAMA_CLOUD_URL=",
                    "BACKEND_URL=http://127.0.0.1:8001",
                    "DATASET=SMAP",
                    "WINDOW_SIZE=100",
                    "THRESHOLD=0.03",
                    "INFERENCE_THRESHOLD=0.03",
                    "SERVER_HOST=0.0.0.0",
                    "SERVER_PORT=8001",
                    "",
                ]
            ),
            encoding="utf-8",
        )


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()


def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:
        return False


def start_process(args, cwd=None, env=None, name="process"):
    proc = subprocess.Popen(args, cwd=cwd, env=env or os.environ.copy())
    PROCESSES.append((name, proc))
    return proc


def cleanup(*_args) -> None:
    for name, proc in reversed(PROCESSES):
        if proc.poll() is None:
            log(f"Stopping {name}...")
            proc.terminate()
    deadline = time.time() + 10
    for _name, proc in reversed(PROCESSES):
        if proc.poll() is None:
            remaining = max(0.0, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()


def wait_for(url: str, label: str, retries: int = 60, delay: float = 2.0) -> None:
    for _ in range(retries):
        if http_ok(url):
            return
        time.sleep(delay)
    raise RuntimeError(f"{label} failed to become healthy.")


def maybe_pull_ollama_model(model: str) -> None:
    prefetch_enabled = os.getenv("OLLAMA_PREFETCH_MODEL", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not prefetch_enabled:
        log("Skipping Ollama model prefetch (OLLAMA_PREFETCH_MODEL=false).")
        return

    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    if result.returncode == 0 and any(line.startswith(model) for line in result.stdout.splitlines()):
        log(f"Ollama model already cached: {model}")
        return

    log(f"Pulling Ollama model: {model}. This runs once when /root/.ollama is cached.")
    pull_result = subprocess.run(["ollama", "pull", model], check=False, env=os.environ.copy())
    if pull_result.returncode != 0:
        log(f"Warning: failed to pull {model}. Chat will still work with cloud keys if configured.")


def main() -> int:
    ensure_env_files()
    load_env_file(ENV_FILE)

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    log("Starting Ollama...")
    ollama_env = os.environ.copy()
    ollama_env["OLLAMA_HOST"] = "0.0.0.0"
    start_process(["ollama", "serve"], env=ollama_env, name="Ollama")

    log("Waiting for Ollama...")
    wait_for(OLLAMA_HEALTH_URL, "Ollama")

    maybe_pull_ollama_model(os.getenv("OLLAMA_MODEL", "llama3.2"))

    log("Starting nginx...")
    start_process(["/usr/sbin/nginx", "-g", "daemon off;"], name="nginx")

    log("Starting ML backend on port 8001...")
    start_process([sys.executable, "serve.py"], cwd=str(APP_ROOT / "Backend"), name="backend")

    log("Waiting for backend...")
    wait_for(BACKEND_HEALTH_URL, "Backend")

    log("Starting API middleware on port 8000...")
    start_process([sys.executable, "main.py"], cwd=str(APP_ROOT / "Middleware"), name="middleware")

    log("All services started.")
    log("Frontend:   http://localhost/")
    log("Middleware: http://localhost:8000")
    log("Backend:    http://localhost:8001")
    log("Ollama:     http://localhost:11434")

    while True:
        for name, proc in PROCESSES:
            code = proc.poll()
            if code is not None:
                log(f"{name} exited with code {code}.")
                return 1
        time.sleep(5)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
