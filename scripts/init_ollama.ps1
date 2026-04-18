# scripts/init_ollama.ps1
# Automates pulling the llama3 model for the Satellite Telemetry Anomaly Detection system.

$OLLAMA_SERVICE = "satellite_ollama"
$MODEL_NAME = "llama3"

Write-Host "Waiting for Ollama service to be ready..." -ForegroundColor Cyan

# Wait for the service to respond
$maxRetries = 30
$retryCount = 0
$ready = $false

while (-not $ready -and $retryCount -lt $maxRetries) {
    try {
        $response = docker exec $OLLAMA_SERVICE ollama list
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
        } else {
            throw "Not ready"
        }
    } catch {
        $retryCount++
        Write-Host "Attempt $($retryCount)/$($maxRetries): Ollama not ready yet, sleeping 2s..."
        Start-Sleep -Seconds 2
    }
}

if ($ready) {
    Write-Host "Ollama service is up. Pulling $MODEL_NAME model..." -ForegroundColor Cyan
    docker exec $OLLAMA_SERVICE ollama pull $MODEL_NAME
    Write-Host "Ollama initialization complete!" -ForegroundColor Green
} else {
    Write-Error "Ollama service failed to start in time. Please check 'docker logs $OLLAMA_SERVICE'."
}
