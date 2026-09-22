<#
.SYNOPSIS
    Downloads the raw Kaggle datasets used by AgriOpt (yield + mandi prices).

.NOTES
    Requires the `kaggle` CLI (installed via requirements.txt) and Kaggle auth.
    Never prints, echoes, or logs the API token.
#>

$ErrorActionPreference = "Stop"

# --- Auth check ------------------------------------------------------------
$hasAuth = $false

if (Test-Path "$HOME\.kaggle\access_token") { $hasAuth = $true }
if (Test-Path "$HOME\.kaggle\access_token.txt") { $hasAuth = $true }
if ($env:KAGGLE_API_TOKEN) { $hasAuth = $true }
if (Test-Path "$HOME\.kaggle\kaggle.json") { $hasAuth = $true }

if (-not $hasAuth) {
    Write-Host "Kaggle authentication not found." -ForegroundColor Red
    Write-Host "Create $HOME\.kaggle\access_token with your Kaggle API token," -ForegroundColor Yellow
    Write-Host "or set `$env:KAGGLE_API_TOKEN, or place kaggle.json at $HOME\.kaggle\kaggle.json." -ForegroundColor Yellow
    exit 1
}

# --- Helper: download a dataset unless its folder already has files --------
function Get-KaggleDataset {
    param(
        [string]$DatasetSlug,
        [string]$DestDir
    )

    if ((Test-Path $DestDir) -and (Get-ChildItem -Path $DestDir -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1)) {
        Write-Host "Skipping $DatasetSlug - $DestDir already has files." -ForegroundColor Cyan
        return
    }

    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null

    Write-Host "Downloading $DatasetSlug into $DestDir ..." -ForegroundColor Green
    kaggle datasets download -d $DatasetSlug -p $DestDir --unzip
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Host "Download failed for $DatasetSlug (exit code $exitCode)." -ForegroundColor Red
        Write-Host "If this was a 403, accept the dataset's terms on Kaggle's website first:" -ForegroundColor Yellow
        Write-Host "  https://www.kaggle.com/datasets/$DatasetSlug" -ForegroundColor Yellow
        exit $exitCode
    }
}

Get-KaggleDataset -DatasetSlug "akshatgupta7/crop-yield-in-indian-states-dataset" -DestDir "data\raw\yield"
Get-KaggleDataset -DatasetSlug "arjunyadav99/indian-agricultural-mandi-prices-20232025" -DestDir "data\raw\prices"

Write-Host "Done." -ForegroundColor Green
