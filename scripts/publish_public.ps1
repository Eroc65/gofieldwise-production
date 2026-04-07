param(
    [string]$PublicRemote = "public",
    [string]$PublicRepoUrl = "https://github.com/Eroc65/gofieldwise-production.git",
    [string]$SourceRef = "main",
    [string]$TargetBranch = "main",
    [string[]]$Commits,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Run-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [string[]]$Arguments = @()
    )

    & git $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git $Command $($Arguments -join ' ')"
    }
}

function Ensure-GitRepo {
    $inside = (& git rev-parse --is-inside-work-tree 2>$null)
    if ($LASTEXITCODE -ne 0 -or $inside.Trim() -ne "true") {
        throw "Run this script from inside a git repository."
    }
}

function Ensure-PublicRemote {
    param([string]$RemoteName, [string]$RemoteUrl)

    $remotes = (& git remote)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to list git remotes."
    }

    if ($remotes -notcontains $RemoteName) {
        Run-Git -Command "remote" -Arguments @("add", $RemoteName, $RemoteUrl)
        Write-Output "Added remote '$RemoteName' -> $RemoteUrl"
        return
    }

    $current = (& git remote get-url $RemoteName).Trim()
    if ($current -ne $RemoteUrl) {
        Run-Git -Command "remote" -Arguments @("set-url", $RemoteName, $RemoteUrl)
        Write-Output "Updated remote '$RemoteName' -> $RemoteUrl"
    } else {
        Write-Output "Remote '$RemoteName' already configured."
    }
}

function Publish-All {
    param([string]$RemoteName, [string]$FromRef, [string]$ToBranch, [bool]$WhatIf)

    $pushSpec = "$FromRef`:$ToBranch"
    if ($WhatIf) {
        Write-Output "[DRY RUN] git push $RemoteName $pushSpec"
        return
    }

    Run-Git -Command "push" -Arguments @($RemoteName, $pushSpec)
}

function Publish-SelectedCommits {
    param(
        [string]$RemoteName,
        [string]$ToBranch,
        [string[]]$CommitList,
        [bool]$WhatIf
    )

    if (-not $CommitList -or $CommitList.Count -eq 0) {
        throw "Commits list is empty."
    }

    $originalBranch = (& git branch --show-current).Trim()
    if ([string]::IsNullOrWhiteSpace($originalBranch)) {
        throw "Cannot determine current branch."
    }

    Run-Git -Command "fetch" -Arguments @($RemoteName, $ToBranch)

    $hasRemoteBranch = $true
    & git rev-parse --verify "$RemoteName/$ToBranch" *> $null
    if ($LASTEXITCODE -ne 0) {
        $hasRemoteBranch = $false
    }

    $tempBranch = "publish/public-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

    if ($hasRemoteBranch) {
        Run-Git -Command "checkout" -Arguments @("-B", $tempBranch, "$RemoteName/$ToBranch")
    } else {
        Run-Git -Command "checkout" -Arguments @("--orphan", $tempBranch)
        Run-Git -Command "reset" -Arguments @("--hard")
    }

    try {
        foreach ($commit in $CommitList) {
            if ($WhatIf) {
                Write-Output "[DRY RUN] git cherry-pick -x $commit"
            } else {
                Run-Git -Command "cherry-pick" -Arguments @("-x", $commit)
            }
        }

        $pushSpec = "$tempBranch`:$ToBranch"
        if ($WhatIf) {
            Write-Output "[DRY RUN] git push $RemoteName $pushSpec"
        } else {
            Run-Git -Command "push" -Arguments @($RemoteName, $pushSpec)
        }
    }
    finally {
        Run-Git -Command "checkout" -Arguments @($originalBranch)
        Run-Git -Command "branch" -Arguments @("-D", $tempBranch)
    }
}

Ensure-GitRepo
Ensure-PublicRemote -RemoteName $PublicRemote -RemoteUrl $PublicRepoUrl

if ($Commits -and $Commits.Count -gt 0) {
    Write-Output "Publishing selected commits to $PublicRemote/$TargetBranch"
    Publish-SelectedCommits -RemoteName $PublicRemote -ToBranch $TargetBranch -CommitList $Commits -WhatIf:$DryRun
} else {
    Write-Output "Publishing full ref '$SourceRef' to $PublicRemote/$TargetBranch"
    Publish-All -RemoteName $PublicRemote -FromRef $SourceRef -ToBranch $TargetBranch -WhatIf:$DryRun
}

Write-Output "Done."
