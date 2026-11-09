# 停止由 scripts\serve_public.ps1 启动的后端与公网隧道
# 只按 data\*.pid 记录、用 taskkill /T 结束自己启动的进程树，绝不按进程名杀进程。

$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "apps\api\app\main.py"))) { $Root = (Get-Location).Path }
$Data = Join-Path $Root "data"

foreach ($name in @("serve.pid", "ssh_tunnel.pid")) {
    $pf = Join-Path $Data $name
    if (Test-Path $pf) {
        $old = (Get-Content $pf -Raw).Trim()
        if ($old -match '^\d+$') {
            & taskkill.exe /T /F /PID $old 2>$null | Out-Null
            Write-Host "[stop] pid=$old（$name 进程树）"
        }
        Remove-Item $pf -Force
    }
}
Write-Host "[done] 后端与隧道已停止（端口 8077 应已释放）。"
