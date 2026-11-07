# 提权执行：彻底重启 Docker Desktop 并等待引擎就绪
# 由 DSH agent 通过 Start-Process -Verb RunAs 调起（用户需点一次 UAC）

$ErrorActionPreference = 'Continue'
$log = 'D:\桌面\机械制图agent\data\docker_restart.log'
function L($msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
  Add-Content -LiteralPath $log -Value $line -Encoding UTF8
}

Set-Content -LiteralPath $log -Value "=== 提权重启开始 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -Encoding UTF8

L "1. 结束所有 Docker 进程"
$procs = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'docker|vpnkit' }
foreach ($p in $procs) {
  try { Stop-Process -Id $p.Id -Force -ErrorAction Stop; L ("   停止 {0} PID={1}" -f $p.ProcessName, $p.Id) }
  catch { L ("   失败 {0} PID={1}: {2}" -f $p.ProcessName, $p.Id, $_.Exception.Message) }
}
Start-Sleep -Seconds 6
$left = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'docker|vpnkit' }
L ("   剩余进程数: " + ($left | Measure-Object).Count)

L "2. 启动 Docker Desktop（提权上下文）"
Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
Start-Sleep -Seconds 10

L "3. 等待引擎就绪（最多 240 秒）"
$ok = $false
for ($i = 0; $i -lt 48; $i++) {
  Start-Sleep -Seconds 5
  $r = & docker version --format '{{.Server.Version}}' 2>&1
  if ($LASTEXITCODE -eq 0 -and "$r" -notmatch 'error') {
    L ("   引擎就绪！Server 版本 " + $r + "（用时 " + (($i+1)*5) + " 秒）")
    $ok = $true
    break
  }
  if ($i % 6 -eq 5) {
    $svc = (Get-Service 'com.docker.service' -ErrorAction SilentlyContinue).Status
    L ("   ...已等 " + (($i+1)*5) + " 秒，com.docker.service=" + $svc)
  }
}

if ($ok) {
  L "4. 引擎信息"
  (& docker info --format '{{.ServerVersion}} | {{.OperatingSystem}} | {{.Driver}} | {{.NCPU}} CPU | {{.MemTotal}} bytes') 2>&1 | ForEach-Object { L ("   " + $_) }
  L "=== 完成：Docker 可用 ==="
} else {
  L "4. 未就绪，收集最后错误"
  (Get-Service 'com.docker.service' -ErrorAction SilentlyContinue | Select-Object Name,Status | Format-Table -AutoSize | Out-String) -split "`n" | ForEach-Object { if ($_.Trim()) { L ("   " + $_.TrimEnd()) } }
  $be = "$env:LOCALAPPDATA\Docker\log\host\com.docker.backend.exe.log"
  if (Test-Path $be) {
    L "   --- backend 日志尾部 ---"
    Get-Content $be -Tail 15 | ForEach-Object { L ("   " + $_) }
  }
  $errs = "$env:LOCALAPPDATA\Docker\backend.error.json"
  if (Test-Path $errs) {
    L ("   backend.error.json 现在 = " + [Math]::Round((Get-Item $errs).Length / 1MB, 1) + " MB")
  }
  L "=== 结束：Docker 仍不可用 ==="
}
