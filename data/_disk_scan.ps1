# 用 robocopy /L（只列不写）+ /XJ（排除 junction）精确统计目录大小
$ErrorActionPreference = 'Continue'

function Get-DirSizeMB([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return -1 }
  $null = robocopy $path NULL /L /S /NJH /NJS /BYTES /XJ /NC /NFL /NDL /R:0 /W:0 2>$null
  # robocopy 的汇总在 stdout；这里改用 /NJH /NJS 后再抓不到，故用 exit 前的输出重定向方式
  return -2
}

# robocopy 汇总行需要 /NJS 去掉；改用手工解析：不用 /NJH /NJS，抓 "字节:" 或 "Bytes :"
function SizeOf([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return $null }
  $out = robocopy $path NULL /L /S /BYTES /XJ /NC /NFL /NDL /R:0 /W:0 2>$null
  $line = $out | Where-Object { $_ -match '^\s*(字节|Bytes)\s*[:：]' } | Select-Object -First 1
  if (-not $line) { return $null }
  if ($line -match '([\d,\.]+)') {
    $num = $matches[1] -replace '[,\.]', ''
    return [double]$num / 1MB
  }
  return $null
}

Write-Output "=== C:\Users\shiyi 下一级目录（robocopy /XJ 排除链接） ==="
$rows = @()
foreach ($d in Get-ChildItem "C:\Users\shiyi" -Directory -Force -ErrorAction SilentlyContinue) {
  $mb = SizeOf $d.FullName
  if ($null -ne $mb) { $rows += [pscustomobject]@{ MB = [Math]::Round($mb, 0); Path = $d.FullName } }
}
$rows | Sort-Object MB -Descending | Select-Object -First 18 |
  ForEach-Object { "  {0,8:N0} MB  {1}" -f $_.MB, $_.Path }

Write-Output "`n=== C:\ 其他一级目录 ==="
foreach ($d in Get-ChildItem "C:\" -Directory -Force -ErrorAction SilentlyContinue |
                    Where-Object { $_.Name -ne 'Users' }) {
  $mb = SizeOf $d.FullName
  if ($null -ne $mb -and $mb -gt 200) {
    "  {0,8:N0} MB  {1}" -f [Math]::Round($mb, 0), $d.FullName
  }
}

Write-Output "`n=== 常见可清理目录确认 ==="
$cands = @(
  "$env:TEMP",
  "C:\Windows\Temp",
  "C:\Windows\SoftwareDistribution\Download",
  "$env:LOCALAPPDATA\pip\Cache",
  "$env:LOCALAPPDATA\npm-cache",
  "$env:LOCALAPPDATA\Yarn\Cache",
  "$env:USERPROFILE\.cache",
  "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache",
  "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache",
  "$env:LOCALAPPDATA\Docker"
)
foreach ($p in $cands) {
  $mb = SizeOf $p
  if ($null -ne $mb) { "  {0,8:N0} MB  {1}" -f [Math]::Round($mb, 0), $p }
}
