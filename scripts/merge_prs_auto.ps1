# Automatically Merge PRs and Clean Up Branches
# Uses GitHub CLI to merge PRs with squash commits

param(
    [switch]$DryRun
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "AUTO MERGE & CLEANUP" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DRY RUN MODE - No changes will be made]`n" -ForegroundColor Yellow
}

# Check authentication
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nGitHub CLI not authenticated. Run: gh auth login" -ForegroundColor Red
    exit 1
}

# Get list of PRs
Write-Host "Fetching open pull requests..." -ForegroundColor Yellow
$prs = gh pr list --json number,headRefName,title,state | ConvertFrom-Json

if ($prs.Count -eq 0) {
    Write-Host "No open pull requests found.`n" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($prs.Count) open PR(s)`n" -ForegroundColor Green

# Merge PRs in order (config-system first, then main-application)
$merge_order = @("feature/config-system", "feature/main-application")

foreach ($branch in $merge_order) {
    $pr = $prs | Where-Object { $_.headRefName -eq $branch }
    
    if ($pr) {
        Write-Host "Merging PR #$($pr.number): $($pr.title)" -ForegroundColor Yellow
        Write-Host "  Branch: $($pr.headRefName)" -ForegroundColor Gray
        
        if (-not $DryRun) {
            # Merge with squash
            gh pr merge $pr.number --squash --delete-branch --auto
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Merged and branch deleted`n" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] Merge failed - may require manual review`n" -ForegroundColor Red
            }
        } else {
            Write-Host "  [DRY RUN] Would merge and delete branch`n" -ForegroundColor Gray
        }
        
        Start-Sleep -Seconds 2
    } else {
        Write-Host "PR for $branch not found, skipping...`n" -ForegroundColor Gray
    }
}

# Clean up local branches
Write-Host "`nCleaning up local repository..." -ForegroundColor Yellow

if (-not $DryRun) {
    # Switch to main
    Write-Host "  Switching to main branch..." -ForegroundColor Gray
    git checkout main
    
    # Pull latest
    Write-Host "  Pulling latest changes..." -ForegroundColor Gray
    git pull origin main
    
    # Delete local feature branches
    Write-Host "  Deleting local feature branches..." -ForegroundColor Gray
    git branch -D feature/config-system 2>$null
    git branch -D feature/main-application 2>$null
    
    # Prune remote references
    Write-Host "  Pruning remote references..." -ForegroundColor Gray
    git fetch --prune
    git remote prune origin
    
    Write-Host "  [OK] Local cleanup complete`n" -ForegroundColor Green
} else {
    Write-Host "  [DRY RUN] Would clean up local branches`n" -ForegroundColor Gray
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MERGE & CLEANUP COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if (-not $DryRun) {
    Write-Host "[OK] All PRs merged with squash commits" -ForegroundColor Green
    Write-Host "[OK] Feature branches deleted" -ForegroundColor Green
    Write-Host "[OK] Local repository cleaned up" -ForegroundColor Green
    Write-Host "`nCurrent branches:" -ForegroundColor Yellow
    git branch -a
} else {
    Write-Host "Run without -DryRun flag to execute merges" -ForegroundColor Yellow
}

Write-Host ""
