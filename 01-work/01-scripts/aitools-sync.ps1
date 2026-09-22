# aitools-sync.ps1
$root = "D:\AI program\workbuddy dic\008-aitools-web"
Set-Location $root
$changes = git status --porcelain
if ($changes) {
    git add -A
    $msg = "chore: auto-sync " + (Get-Date -Format "yyyy-MM-dd HH:mm")
    git commit -m $msg | Out-Null
    Write-Output ("COMMITTED: " + $msg)
} else {
    Write-Output "NO_CHANGES"
}
git push origin master
Write-Output "PUSH_DONE"
