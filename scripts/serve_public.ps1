# 一键把《核反应堆物理 AI 助教》发布成"别人电脑浏览器能打开"的服务
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts\serve_public.ps1
# 停止：
#   powershell -ExecutionPolicy Bypass -File scripts\stop_serve.ps1
#
# 设计要点（重要）：
#   · 用 Win32_Process.Create 起进程，父进程是 WMI 服务而不是当前终端 —— 关掉终端/退出会话后服务仍然在跑；
#   · 后端故意用 D:\python\python.exe（Windows 防火墙已有它的入站放行规则），依赖走项目 venv 的 site-packages；
#   · 公网用 localhost.run 的 SSH 反向隧道（免注册），得到 https://xxxx.lhr.life；
#   · 只按 data\*.pid 记录停止自己启动的进程，绝不按进程名杀进程。
#
# 注意：公网链接是临时隧道，本机重启/断网/隧道退出后 URL 会变；固定地址请用 Render（见 DEPLOY.md）。

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "apps\api\app\main.py"))) { $Root = (Get-Location).Path }
$Data = Join-Path $Root "data"
New-Item -ItemType Directory -Force -Path $Data | Out-Null
$TunnelLog = Join-Path $env:TEMP "rp_ssh_tunnel.log"

function Stop-Old([string]$pidFile) {
    if (Test-Path $pidFile) {
        $old = (Get-Content $pidFile -Raw).Trim()
        if ($old -match '^\d+$') {
            & taskkill.exe /T /F /PID $old 2>$null | Out-Null
            Write-Host "[stop] old pid=$old"
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

# 0) 先停掉上一次由本脚本启动的（只按记录 PID）
Stop-Old (Join-Path $Data "serve.pid")
Stop-Old (Join-Path $Data "ssh_tunnel.pid")
Start-Sleep -Seconds 1

# 1) 后端（WMI 起，0.0.0.0:8077）
$sp = Join-Path $Root "apps\api\.venv\Lib\site-packages"
$api = Join-Path $Root "apps\api"
$serveLog = Join-Path $Data "serve_lan.log"
$serveCmd = 'cmd /c set "PYTHONPATH=' + $sp + ';' + $api + '" && set "PYTHONIOENCODING=utf-8" && "D:\python\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8077 >> "' + $serveLog + '" 2>&1'
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $serveCmd; CurrentDirectory = $api }
if ($r.ReturnValue -ne 0) { Write-Host "[fail] 后端启动失败 rc=$($r.ReturnValue)"; exit 1 }
$r.ProcessId | Set-Content (Join-Path $Data "serve.pid") -Encoding ascii
Write-Host "[ok] 后端进程 pid=$($r.ProcessId)（日志 data\serve_lan.log）"

$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 1000
    try {
        $h = Invoke-WebRequest -Uri "http://127.0.0.1:8077/api/health" -TimeoutSec 3 -UseBasicParsing
        if ($h.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
}
if (-not $healthy) { Write-Host "[fail] 健康检查未通过，查看 data\serve_lan.log"; exit 1 }
$h = Invoke-WebRequest -Uri "http://127.0.0.1:8077/api/health" -TimeoutSec 5 -UseBasicParsing | ConvertFrom-Json
Write-Host "[ok] 健康检查：语料 $($h.chunks) 块 / 工具 $($h.tools.Count) 个 / 图谱 $($h.nodes) 节点"

# 2) 公网隧道（免注册）
$tunnelCmdFile = Join-Path $Data "start_tunnel.cmd"
$batch = '@echo off' + "`r`n" +
    '"C:\Windows\System32\OpenSSH\ssh.exe" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -T -R 80:localhost:8077 nokey@localhost.run >> "%TEMP%\rp_ssh_tunnel.log" 2>&1' + "`r`n"
Set-Content -LiteralPath $tunnelCmdFile -Value $batch -Encoding Default
Remove-Item $TunnelLog -ErrorAction SilentlyContinue
$rt = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = ('cmd /c "' + $tunnelCmdFile + '"'); CurrentDirectory = $Data }
$rt.ProcessId | Set-Content (Join-Path $Data "ssh_tunnel.pid") -Encoding ascii

$public = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Path $TunnelLog) {
        $txt = Get-Content $TunnelLog -Raw -ErrorAction SilentlyContinue
        $m = [regex]::Match($txt, "https://[A-Za-z0-9]+\.lhr\.life")
        if ($m.Success) { $public = $m.Value; break }
    }
}
if ($public) {
    $public | Set-Content (Join-Path $Data "public_url.txt") -Encoding ascii
    Write-Host "[ok] 公网地址：$public"
} else {
    Write-Host "[warn] 未解析到公网地址，查看 $TunnelLog（隧道 pid=$($rt.ProcessId)）"
}

$lan = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254*" } |
    Select-Object -First 1 -ExpandProperty IPAddress)
Write-Host ""
Write-Host "================ 访问地址 ================"
Write-Host "同网络（校园/局域网）： http://${lan}:8077/"
if ($public) { Write-Host "公网（任何电脑）：     $public/" }
Write-Host "教师端：               <上面的地址>/admin"
Write-Host "健康检查：             <上面的地址>/api/health"
Write-Host "停止：                 powershell -ExecutionPolicy Bypass -File scripts\stop_serve.ps1"
Write-Host "=========================================="
Write-Host "提示：本机需保持开机、不休眠；公网链接是本机隧道，重启后 URL 会变。"
