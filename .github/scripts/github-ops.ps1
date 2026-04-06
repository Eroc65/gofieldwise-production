param(
    [ValidateSet("check-secrets", "set-smoke-secrets", "trigger-staging", "trigger-production", "status")]
    [string]$Action = "status",
    [string]$Repo = "Eroc65/auto-gpt",
    [string]$StagingApiBaseUrl,
    [string]$StagingSmokeEmail,
    [string]$StagingSmokePassword,
    [string]$ProductionApiBaseUrl,
    [string]$ProductionSmokeEmail,
    [string]$ProductionSmokePassword
)

$ErrorActionPreference = "Stop"

function Require-Gh {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "GitHub CLI (gh) is not installed or not in PATH."
    }
    $null = gh auth status 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI is not authenticated. Run: gh auth login"
    }
}

function Get-SecretNames {
    $lines = gh secret list --repo $Repo
    if (-not $lines) {
        return @()
    }

    $names = @()
    foreach ($line in $lines) {
        if ($line -match "^NAME") {
            continue
        }
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }
        $name = ($trimmed -split "\s+")[0]
        $names += $name
    }
    return $names
}

function Show-SecretHealth {
    $required = @(
        "RENDER_FRONTEND_DEPLOY_HOOK_URL",
        "RENDER_BACKEND_DEPLOY_HOOK_URL",
        "RENDER_STAGING_FRONTEND_DEPLOY_HOOK_URL",
        "RENDER_STAGING_BACKEND_DEPLOY_HOOK_URL",
        "STAGING_API_BASE_URL",
        "STAGING_SMOKE_EMAIL",
        "STAGING_SMOKE_PASSWORD",
        "PRODUCTION_API_BASE_URL",
        "PRODUCTION_SMOKE_EMAIL",
        "PRODUCTION_SMOKE_PASSWORD"
    )

    $existing = Get-SecretNames
    $missing = @()
    foreach ($name in $required) {
        if ($existing -notcontains $name) {
            $missing += $name
        }
    }

    Write-Output "Repository: $Repo"
    Write-Output "Existing secrets: $($existing.Count)"
    if ($missing.Count -eq 0) {
        Write-Output "Missing secrets: none"
    } else {
        Write-Output "Missing secrets:"
        $missing | ForEach-Object { Write-Output "- $_" }
    }
}

function Set-SmokeSecrets {
    $requiredValues = @{
        "STAGING_API_BASE_URL" = $StagingApiBaseUrl
        "STAGING_SMOKE_EMAIL" = $StagingSmokeEmail
        "STAGING_SMOKE_PASSWORD" = $StagingSmokePassword
        "PRODUCTION_API_BASE_URL" = $ProductionApiBaseUrl
        "PRODUCTION_SMOKE_EMAIL" = $ProductionSmokeEmail
        "PRODUCTION_SMOKE_PASSWORD" = $ProductionSmokePassword
    }

    foreach ($k in $requiredValues.Keys) {
        if ([string]::IsNullOrWhiteSpace($requiredValues[$k])) {
            throw "Missing required parameter for $k"
        }
    }

    foreach ($pair in $requiredValues.GetEnumerator()) {
        gh secret set $pair.Key --repo $Repo --body $pair.Value | Out-Null
        Write-Output "Set $($pair.Key)"
    }
}

function Trigger-Workflow([string]$workflowName) {
    gh workflow run $workflowName --repo $Repo
    Start-Sleep -Seconds 2
    $runs = gh run list --repo $Repo --workflow $workflowName --limit 1 --json databaseId,status,conclusion,displayTitle,createdAt,url | ConvertFrom-Json
    if ($runs.Count -gt 0) {
        $run = $runs[0]
        Write-Output "Triggered: $workflowName"
        Write-Output "Run ID: $($run.databaseId)"
        Write-Output "Status: $($run.status)"
        Write-Output "Conclusion: $($run.conclusion)"
        Write-Output "URL: $($run.url)"
    }
}

Require-Gh

switch ($Action) {
    "check-secrets" {
        Show-SecretHealth
    }
    "set-smoke-secrets" {
        Set-SmokeSecrets
        Show-SecretHealth
    }
    "trigger-staging" {
        Trigger-Workflow -workflowName "Deploy Staging"
    }
    "trigger-production" {
        Trigger-Workflow -workflowName "Deploy Production"
    }
    "status" {
        Show-SecretHealth
        Write-Output "Latest Deploy Staging run:"
        gh run list --repo $Repo --workflow "Deploy Staging" --limit 1
        Write-Output "Latest Deploy Production run:"
        gh run list --repo $Repo --workflow "Deploy Production" --limit 1
        Write-Output "Latest Post Deploy Smoke run:"
        gh run list --repo $Repo --workflow "Post Deploy Smoke" --limit 1
    }
}
