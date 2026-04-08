param(
    [ValidateSet("check-secrets", "set-smoke-secrets", "trigger-staging", "trigger-production", "validate-hooks", "status")]
    [string]$Action = "status",
    [string]$Repo,
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

function Resolve-Repo {
    if (-not [string]::IsNullOrWhiteSpace($Repo)) {
        return $Repo
    }

    $detected = gh repo view --json nameWithOwner -q .nameWithOwner 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($detected)) {
        throw "Unable to resolve repository. Pass -Repo <owner/repo> or run inside a cloned GitHub repository."
    }

    return $detected.Trim()
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

function Get-SecretValue([string]$name) {
    $value = gh secret list --repo $Repo --json name,updatedAt | ConvertFrom-Json
    if (-not $value) {
        return $null
    }
    $match = $value | Where-Object { $_.name -eq $name } | Select-Object -First 1
    if (-not $match) {
        return $null
    }
    return "present"
}

function Test-RenderDeployHookFormat([string]$hookUrl) {
    if ([string]::IsNullOrWhiteSpace($hookUrl)) {
        return $false
    }
    return $hookUrl -match "^https://api\.render\.com/deploy/srv-[A-Za-z0-9]+\?key=[A-Za-z0-9]+$"
}

function Validate-HookPattern([string]$secretName, [string]$value) {
    if (-not (Test-RenderDeployHookFormat $value)) {
        throw "$secretName is not a valid Render deploy hook URL format. Expected: https://api.render.com/deploy/srv-...?..."
    }
}

function Validate-DeployHooks {
    $requiredHookNames = @(
        "RENDER_FRONTEND_DEPLOY_HOOK_URL",
        "RENDER_BACKEND_DEPLOY_HOOK_URL",
        "RENDER_STAGING_FRONTEND_DEPLOY_HOOK_URL",
        "RENDER_STAGING_BACKEND_DEPLOY_HOOK_URL"
    )

    $missing = @()
    foreach ($name in $requiredHookNames) {
        $present = Get-SecretValue -name $name
        if (-not $present) {
            $missing += $name
        }
    }

    if ($missing.Count -gt 0) {
        Write-Output "Missing deploy hook secrets:"
        $missing | ForEach-Object { Write-Output "- $_" }
        throw "Deploy hook validation failed."
    }

    Write-Output "Deploy hook secret names present."
    Write-Output "Note: GitHub does not allow reading secret values via CLI/API."
    Write-Output "Run workflow validation steps to verify hook URL formats at execution time."
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
$Repo = Resolve-Repo

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
    "validate-hooks" {
        Validate-DeployHooks
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
