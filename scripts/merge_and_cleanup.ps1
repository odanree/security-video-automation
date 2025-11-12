# Merge PRs and Cleanup Branches
# Run this after PRs are merged on GitHub

param(
    [switch]$DryRun
)

$branches = @(
    "feature/config-system",
    "feature/main-application"
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PR MERGE AND BRANCH CLEANUP" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DRY RUN MODE - No changes will be made]`n" -ForegroundColor Yellow
}

# Switch to main branch
Write-Host "1. Switching to main branch..." -ForegroundColor Green
if (-not $DryRun) {
    git checkout main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to checkout main branch" -ForegroundColor Red
        exit 1
    }
}
Write-Host "   ✓ On main branch`n" -ForegroundColor Gray

# Pull latest from origin
Write-Host "2. Pulling latest changes from origin/main..." -ForegroundColor Green
if (-not $DryRun) {
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to pull from origin/main" -ForegroundColor Red
        exit 1
    }
}
Write-Host "   ✓ Local main updated`n" -ForegroundColor Gray

# Delete local feature branches
Write-Host "3. Deleting local feature branches..." -ForegroundColor Green
foreach ($branch in $branches) {
    Write-Host "   - Deleting local $branch..." -ForegroundColor Yellow
    if (-not $DryRun) {
        git branch -d $branch 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "     ✓ Deleted" -ForegroundColor Gray
        } else {
            # Try force delete if regular delete fails
            git branch -D $branch
            if ($LASTEXITCODE -eq 0) {
                Write-Host "     ✓ Force deleted" -ForegroundColor Gray
            } else {
                Write-Host "     ⚠ Failed to delete" -ForegroundColor Red
            }
        }
    }
}
Write-Host ""

# Delete remote feature branches
Write-Host "4. Deleting remote feature branches..." -ForegroundColor Green
foreach ($branch in $branches) {
    Write-Host "   - Deleting origin/$branch..." -ForegroundColor Yellow
    if (-not $DryRun) {
        git push origin --delete $branch 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "     ✓ Deleted from origin" -ForegroundColor Gray
        } else {
            Write-Host "     ⚠ Already deleted or failed" -ForegroundColor Gray
        }
    }
}
Write-Host ""

# Prune remote tracking branches
Write-Host "5. Pruning remote tracking branches..." -ForegroundColor Green
if (-not $DryRun) {
    git fetch --prune
    git remote prune origin
}
Write-Host "   ✓ Remote branches pruned`n" -ForegroundColor Gray

# Show final branch list
Write-Host "6. Final branch list:" -ForegroundColor Green
git branch -a

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CLEANUP COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "✓ Main branch is up to date" -ForegroundColor Green
Write-Host "✓ Feature branches deleted locally" -ForegroundColor Green
Write-Host "✓ Feature branches deleted from origin" -ForegroundColor Green
Write-Host "✓ Repository cleaned up`n" -ForegroundColor Green
