param(
    [string]$BaseUrl = "",
    [string]$HealthPath = "",
    [int]$StartupTimeoutSeconds = 30,
    [int]$ProbeTimeoutSeconds = 4
)

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = $env:AGENT_MODEL_BASE_URL
}
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://localhost:1234/v1"
}

if ([string]::IsNullOrWhiteSpace($HealthPath)) {
    $HealthPath = $env:AGENT_MODEL_HEALTH_PATH
}
if ([string]::IsNullOrWhiteSpace($HealthPath)) {
    $HealthPath = "/models"
}

function Get-HealthUrl {
    param(
        [string]$Base,
        [string]$Path
    )

    $b = $Base.TrimEnd("/")
    if ($Path.StartsWith("/")) {
        return "$b$Path"
    }
    return "$b/$Path"
}

function Test-ModelBackend {
    param(
        [string]$Url,
        [int]$TimeoutSec = 4
    )

    try {
        $null = Invoke-RestMethod -Method GET -Uri $Url -TimeoutSec $TimeoutSec
        return $true
    }
    catch {
        return $false
    }
}

function Start-BackendFromCommand {
    param([string]$Command)

    if ([string]::IsNullOrWhiteSpace($Command)) {
        return $false
    }

    Write-Host "[ensure_model_backend] Starting backend via AGENT_MODEL_START_CMD"
    Start-Process powershell -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $Command
    ) -WindowStyle Hidden | Out-Null

    return $true
}

function Start-LMStudioIfPresent {
    $candidates = @(
        $env:LMSTUDIO_EXE,
        "$env:LOCALAPPDATA\Programs\LM Studio\LM Studio.exe",
        "$env:ProgramFiles\LM Studio\LM Studio.exe",
        "$env:ProgramFiles(x86)\LM Studio\LM Studio.exe"
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            Write-Host "[ensure_model_backend] Starting LM Studio: $candidate"
            Start-Process -FilePath $candidate | Out-Null
            return $true
        }
    }

    return $false
}

function Start-OllamaIfRelevant {
    param([string]$Base)

    if ($Base -notmatch "11434") {
        return $false
    }

    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if ($null -ne $ollama) {
        Write-Host "[ensure_model_backend] Starting Ollama server"
        Start-Process -FilePath $ollama.Source -ArgumentList @("serve") -WindowStyle Hidden | Out-Null
        return $true
    }

    return $false
}

$healthUrl = Get-HealthUrl -Base $BaseUrl -Path $HealthPath
Write-Host "[ensure_model_backend] Checking $healthUrl"

if (Test-ModelBackend -Url $healthUrl -TimeoutSec $ProbeTimeoutSeconds) {
    Write-Host "[ensure_model_backend] Backend already healthy"
    exit 0
}

$started = $false

if (-not $started) {
    $started = Start-BackendFromCommand -Command $env:AGENT_MODEL_START_CMD
}

if (-not $started) {
    $started = Start-OllamaIfRelevant -Base $BaseUrl
}

if (-not $started) {
    $started = Start-LMStudioIfPresent
}

if (-not $started) {
    Write-Error "[ensure_model_backend] Could not start a backend automatically. Configure AGENT_MODEL_START_CMD or LMSTUDIO_EXE."
    exit 1
}

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    if (Test-ModelBackend -Url $healthUrl -TimeoutSec $ProbeTimeoutSeconds) {
        Write-Host "[ensure_model_backend] Backend became healthy"
        exit 0
    }
}

Write-Error "[ensure_model_backend] Backend did not become healthy within $StartupTimeoutSeconds seconds"
exit 1
