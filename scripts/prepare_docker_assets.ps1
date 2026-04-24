param(
    [string]$NginxSourceImage = "web-server:blue"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$dockerDir = Join-Path $repoRoot "docker"
$nginxRuntimeDir = Join-Path $dockerDir "nginx-runtime"
$wheelDir = Join-Path $dockerDir "wheels"
$requirementsFile = Join-Path $dockerDir "runtime-requirements.txt"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$tempContainer = "sat-nginx-extract"

if (-not (Test-Path $venvPython)) {
    throw "Expected Python at $venvPython. Create the project .venv first."
}

if (-not (Test-Path $requirementsFile)) {
    throw "Missing runtime requirements file at $requirementsFile."
}

New-Item -ItemType Directory -Force $nginxRuntimeDir | Out-Null
New-Item -ItemType Directory -Force $wheelDir | Out-Null

Get-ChildItem $nginxRuntimeDir -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne ".gitkeep" } |
    Remove-Item -Recurse -Force
Get-ChildItem $wheelDir -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

docker image inspect $NginxSourceImage | Out-Null

try {
    docker rm -f $tempContainer 2>$null | Out-Null
} catch {
}

docker create --name $tempContainer $NginxSourceImage | Out-Null
docker start $tempContainer | Out-Null
try {
    $nginxFiles = @{
        "nginx" = "/usr/sbin/nginx"
        "mime.types" = "/etc/nginx/mime.types"
        "libcrypt.so.1" = "/lib/x86_64-linux-gnu/libcrypt.so.1"
        "libpcre2-8.so.0" = "/lib/x86_64-linux-gnu/libpcre2-8.so.0"
        "libssl.so.3" = "/lib/x86_64-linux-gnu/libssl.so.3"
        "libcrypto.so.3" = "/lib/x86_64-linux-gnu/libcrypto.so.3"
        "libz.so.1" = "/lib/x86_64-linux-gnu/libz.so.1"
    }

    foreach ($fileName in $nginxFiles.Keys) {
        $resolvedSource = (docker exec $tempContainer sh -lc "readlink -f '$($nginxFiles[$fileName])'").Trim()
        if (-not $resolvedSource) {
            throw "Failed to resolve $($nginxFiles[$fileName]) inside $tempContainer."
        }
        docker cp "${tempContainer}:$resolvedSource" (Join-Path $nginxRuntimeDir $fileName)
    }
} finally {
    docker rm -f $tempContainer | Out-Null
}

$requirements = Get-Content $requirementsFile |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -and -not $_.StartsWith("#") }

$torchRequirements = @($requirements | Where-Object { $_ -like "torch==*" })
$pypiRequirements = @($requirements | Where-Object { $_ -notlike "torch==*" })

$commonArgs = @(
    "-m", "pip", "download",
    "--dest", $wheelDir,
    "--only-binary=:all:",
    "--platform", "linux_x86_64",
    "--platform", "manylinux2014_x86_64",
    "--platform", "manylinux_2_17_x86_64",
    "--platform", "manylinux_2_28_x86_64",
    "--implementation", "cp",
    "--python-version", "311",
    "--abi", "cp311",
    "--timeout", "180",
    "--retries", "8"
)

if ($pypiRequirements.Count -gt 0) {
    Write-Host "Downloading runtime wheels from PyPI..."
    & $venvPython @commonArgs --index-url https://pypi.org/simple @pypiRequirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download runtime wheels from PyPI."
    }
}

if ($torchRequirements.Count -gt 0) {
    Write-Host "Downloading CUDA-enabled torch wheel and its dependencies..."
    & $venvPython @commonArgs `
        --index-url https://download.pytorch.org/whl/cu121 `
        --extra-index-url https://pypi.org/simple `
        @torchRequirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download torch wheels from the CUDA index."
    }

    $torchWheel = Get-ChildItem $wheelDir -Filter "torch-*.whl" | Select-Object -First 1
    if (-not $torchWheel) {
        throw "Torch wheel was not downloaded into $wheelDir."
    }

    # Torch 2.5.1+cu121 on Linux/x86_64 requires these CUDA runtime wheels.
    $linuxTorchDeps = @(
        "nvidia-cuda-nvrtc-cu12==12.1.105",
        "nvidia-cuda-runtime-cu12==12.1.105",
        "nvidia-cuda-cupti-cu12==12.1.105",
        "nvidia-cudnn-cu12==9.1.0.70",
        "nvidia-cublas-cu12==12.1.3.1",
        "nvidia-cufft-cu12==11.0.2.54",
        "nvidia-curand-cu12==10.3.2.106",
        "nvidia-cusolver-cu12==11.4.5.107",
        "nvidia-cusparse-cu12==12.1.0.106",
        "nvidia-nccl-cu12==2.21.5",
        "nvidia-nvtx-cu12==12.1.105",
        "triton==3.1.0"
    )

    if ($linuxTorchDeps.Count -gt 0) {
        Write-Host "Downloading CUDA runtime dependency wheels..."
        & $venvPython @commonArgs --index-url https://pypi.org/simple @linuxTorchDeps
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to download CUDA runtime dependency wheels."
        }
    }
}

if (-not (Get-ChildItem $wheelDir -Filter "torch-*.whl" -ErrorAction SilentlyContinue)) {
    throw "Torch wheel was not downloaded into $wheelDir."
}

if (-not (Get-ChildItem $wheelDir -Filter "fastapi-*.whl" -ErrorAction SilentlyContinue)) {
    throw "FastAPI wheel was not downloaded into $wheelDir."
}

if (-not (Get-ChildItem $wheelDir -Filter "nvidia-cuda-nvrtc-cu12-*.whl" -ErrorAction SilentlyContinue)) {
    throw "CUDA runtime dependency wheels were not downloaded into $wheelDir."
}

Write-Host "Prepared nginx runtime assets in $nginxRuntimeDir"
Write-Host "Prepared offline wheels in $wheelDir"
