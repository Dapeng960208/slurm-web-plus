param(
    [string]$Workflow,
    [string]$Branch = "main",
    [int]$PollIntervalSeconds = 30,
    [int]$TimeoutMinutes = 30,
    [string]$OutputRoot = ".ci-results/github",
    [switch]$DownloadArtifacts = $true,
    [switch]$ShowFailedLog = $true
)

$ErrorActionPreference = "Stop"

$fetchScript = Join-Path $PSScriptRoot "fetch-github-ci-result.ps1"
if (-not (Test-Path $fetchScript)) {
    throw "Missing script: $fetchScript"
}

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
$lastRunId = $null

while ((Get-Date) -lt $deadline) {
    $run = & $fetchScript -Workflow $Workflow -Branch $Branch -OutputRoot $OutputRoot | ConvertFrom-Json
    if (-not $lastRunId) {
        $lastRunId = [string]$run.run_id
    }

    if ($run.status -eq "completed") {
        $arguments = @{
            RunId = [string]$run.run_id
            OutputRoot = $OutputRoot
        }
        if ($DownloadArtifacts) {
            $arguments.DownloadArtifacts = $true
        }
        if ($ShowFailedLog) {
            $arguments.ShowFailedLog = $true
        }

        & $fetchScript @arguments
        exit 0
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}

throw "Timed out waiting for workflow '$Workflow' on branch '$Branch' to complete within $TimeoutMinutes minutes."
