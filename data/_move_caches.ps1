# 把已有缓存搬到 D 盘：复制 → 校验大小 → 确认后再删源目录
$ErrorActionPreference = 'Continue'

function Get-DirMB([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { return 0 }
  $s = (Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
  if ($null -eq $s) { return 0 }
  return [Math]::Round($s / 1MB, 1)
}

function Move-Cache([string]$src, [string]$dst, [string]$label) {
  Write-Output ("=" * 66)
  Write-Output ("[$label]")
  if (-not (Test-Path -LiteralPath $src)) {
    Write-Output ("  源不存在，跳过: $src")
    return
  }
  $srcMB = Get-DirMB $src
  Write-Output ("  源 : $src  ({0:N0} MB)" -f $srcMB)
  Write-Output ("  目标: $dst")
  if ($srcMB -le 0) {
    Write-Output "  源为空，只建目标目录"
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    return
  }
  New-Item -ItemType Directory -Path $dst -Force | Out-Null

  # 复制（/E 含空目录，/NFL /NDL 精简输出，/R:1 少重试）
  $null = robocopy $src $dst /E /NFL /NDL /NJH /NJS /NC /NS /NP /R:1 /W:1 2>&1
  $dstMB = Get-DirMB $dst
  Write-Output ("  复制完成，目标大小 {0:N0} MB" -f $dstMB)

  # 允许 2% 误差（robocopy 可能跳过个别被占用文件）
  $ratio = if ($srcMB -gt 0) { $dstMB / $srcMB } else { 1 }
  Write-Output ("  完整度: {0:P1}" -f $ratio)

  if ($ratio -ge 0.98) {
    try {
      Remove-Item -LiteralPath $src -Recurse -Force -ErrorAction Stop
      Write-Output ("  已删除源目录 ✅  释放 {0:N0} MB" -f $srcMB)
    } catch {
      Write-Output ("  [!] 源目录删除失败（可能被占用）：" + $__.Exception.Message)
      Write-Output ("      请稍后手动删: $src")
    }
  } else {
    Write-Output "  [!] 复制不完整，保留源目录不动，请人工检查"
  }
}

$before = [Math]::Round((Get-PSDrive C).Free / 1GB, 2)
Write-Output ("C 盘可用（搬迁前）: $before GB`n")

Move-Cache "$env:LOCALAPPDATA\npm-cache"      "D:\npm-cache"       "npm 缓存"
Move-Cache "$env:USERPROFILE\.cache\huggingface" "D:\hf-cache"     "HuggingFace 模型缓存"
Move-Cache "$env:USERPROFILE\.cache\puppeteer"   "D:\puppeteer-cache" "puppeteer 浏览器缓存"

$after = [Math]::Round((Get-PSDrive C).Free / 1GB, 2)
Write-Output ("`n" + ("=" * 66))
Write-Output ("C 盘可用: $before GB → $after GB  （+{0:N1} GB）" -f ($after - $before))
