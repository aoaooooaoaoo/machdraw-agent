# 16 · Docker 打不开的排查与修复记录

> 症状：Docker Desktop 双击后"进不去"，`docker` 命令报
> `open //./pipe/docker_engine: The system cannot find the file specified`。
>
> ## ✅ 已解决（2026-11-07 10:07）
> 一共踩了 **3 个坑**，全部修完并实测通过：
> 1. `~/.docker/daemon.json` 带 UTF-8 BOM → 后端启动即崩（根因）
> 2. `registry-mirrors` 里 `registry.docker-cn.com` **早已停服** → 拉镜像/解析构建元数据时 EOF
> 3. `Dockerfile` 漏 `COPY apps/api/static` → 容器里教师端 `/admin` 404
>
> 最终结果：镜像 434MB，`docker compose up -d` 起容器 healthy，
> `/api/health`、`/`、`/admin`、`/api/chat`（真问一句出 three_view + evidence）全部通过。

---

## 一、现场诊断（实测）

| 检查项 | 结果 | 说明 |
|---|---|---|
| `docker.exe` | 28.4.0 存在 | `C:\Program Files\Docker\Docker\resources\bin\docker.exe` |
| Docker Desktop 程序 | 存在 | `C:\Program Files\Docker\Docker\Docker Desktop.exe` |
| `com.docker.service` | **Stopped** | 启动它需要管理员权限 |
| WSL2 | **正常** | 有 `Ubuntu`、`docker-desktop`、`Ubuntu-20.04` 三个发行版，可启动 |
| 虚拟化 | 正常 | `HypervisorPresent=True`（Hyper-V 在跑，所以固件标志显示 False 是正常的） |
| 用户在 `docker-users` 组 | 是 | 权限不是问题 |
| `\\.\pipe\docker_engine` | 不存在 | 引擎从未起来 |
| `backend.error.json` | **944 MB 且不再增长** | 崩溃循环留下的错误转储 |

## 二、真因（从错误转储里挖出来的）

错误转储第一条就写着：

```
formatting daemon.json: parsing JSON: invalid character 'ï' looking for beginning of value
```

`ï` 是 UTF-8 BOM（`EF BB BF`）被当成 latin1 读的第一个字节。
也就是说：**`~/.docker/daemon.json` 文件开头带了 BOM，Docker 解析 JSON 失败，
后端在初始化阶段就崩了**，于是：服务起不来 → 引擎起不来 → 管道不存在 → 客户端连不上 →
每次重试都弹一次错误框并往 `backend.error.json` 追加，滚到 944 MB。

这是典型的"文件不是用户手写、而是被某个编辑器/脚本以带 BOM 方式保存"造成的。

## 三、已做的修复（有备份）

### ✅ 已修：`C:\Users\shiyi\.docker\daemon.json`

| | |
|---|---|
| 原状 | 436 字节，**带 BOM**（`EF BB BF` 开头） |
| 备份 | `C:\Users\shiyi\.docker\daemon.json.bak-20261107-095340` |
| 修复 | 去掉 BOM，重写为合法 JSON（内容保持不变，仅规范缩进），232 字节 |
| 复核 | `json.loads()` 通过，BOM=False |

修复后内容：
```json
{
  "experimental": false,
  "registry-mirrors": [
    "https://registry.docker-cn.com",
    "https://docker.mirrors.ustc.edu.cn"
  ],
  "builder": { "gc": { "defaultKeepStorage": "20GB", "enabled": true } }
}
```

### ✅ 已修：`registry-mirrors` 里的死源

你原配置里有两个镜像源，其中 `https://registry.docker-cn.com` 早在 2018 年就停服了。
它在列表第一位，导致**构建时解析 `FROM node:22-alpine` 的元数据直接 EOF 失败**
（`docker pull` 会继续尝试后续源所以能成功，但 BuildKit 的元数据解析不会）。

处理：已从 `~/.docker/daemon.json` 移除该源，只保留 `https://docker.mirrors.ustc.edu.cn`。
（daemon.json 的改动要**重启引擎**才生效；本次靠先把基础镜像 `docker pull` 到本地，
让构建直接命中本地镜像绕过了这一步。将来重启 Docker 后新配置自动生效。）

### ⚠ 未修完（但不影响使用）：`C:\ProgramData\Docker\config\daemon.json`

| | |
|---|---|
| 原状 | 85 字节，**不是合法 JSON**（键没加引号） |
| 备份 | 已备份到 `daemon.json.bak-20261107-095340` |
| 状态 | **写入被拒绝**（需要管理员权限），内容尚未改 |
| 原文 | `{ dns: [8.8.8.8, 8.8.4.4], experimental: false, features: { buildkit: true } }` |

正确写法应为：
```json
{
  "dns": ["8.8.8.8", "8.8.4.4"],
  "experimental": false,
  "features": { "buildkit": true }
}
```

## 四、~~需要你做的一件事~~（已完成）

> 2026-11-07 10:06 用户重启 Docker Desktop 后引擎正常起来，
> 说明 **BOM 就是唯一的启动阻塞点**，改完即通。以下保留原始指引备查。

我这边是**非管理员会话**，而且本会话的权限提升被系统自动拒了，
所以没法替你重启 Docker Desktop（它当前是提权实例，非提权 shell 杀不掉）。
请做其中一种：

**方式 A（推荐，两次点击）**
1. 右下角托盘找到 Docker 鲸鱼图标 → 右键 → **Quit Docker Desktop**
2. 重新双击 Docker Desktop；**如果弹 UAC，点「是」**

**方式 B（任务管理器）**
1. `Ctrl+Shift+Esc` → 找到所有 `Docker Desktop` / `com.docker.backend` → 结束任务
2. 重新双击 Docker Desktop，UAC 点「是」

做完跟我说一声，我立刻跑 `docker build` 把配置坐实。

### 如果还弹错误框

大概率就是上面那个 **ProgramData 的非法 JSON**。以管理员身份开一个 PowerShell，粘这段：

```powershell
$p = "C:\ProgramData\Docker\config\daemon.json"
Copy-Item $p "$p.bak-$(Get-Date -Format yyyyMMdd-HHmmss)" -Force
'{
  "dns": ["8.8.8.8", "8.8.4.4"],
  "experimental": false,
  "features": { "buildkit": true }
}' | Set-Content -LiteralPath $p -Encoding utf8 -NoNewline
Get-Content $p
```
（`Set-Content -Encoding utf8` 在 PowerShell 5.1 会带 BOM，所以更稳的是用记事本另存为"UTF-8 无 BOM"，或直接用我给的 `Set-Content ... -Encoding ascii`。）

然后重启 Docker Desktop。

## 五、建议顺手清理的垃圾

| 文件 | 大小 | 说明 |
|---|---|---|
| `C:\Users\shiyi\AppData\Local\Docker\backend.error.json` | **944 MB** | 崩溃循环的错误转储，纯垃圾，可删 |

这个我没删——它不是我创建的，按你定的规矩不擅自删你的文件。你确认后我可以删，或者你自己删。

## 六、如果 Docker Desktop 实在修不好（备选方案，需要你同意）

你的 WSL2 是好的，可以**在 Ubuntu 发行版里直接装 Docker Engine**，完全绕开 Docker Desktop：

```powershell
wsl -d Ubuntu -u root -e bash -c "apt-get update && apt-get install -y docker.io"
wsl -d Ubuntu -u root -e service docker start
wsl -d Ubuntu -e docker ps
```

好处：不需要 Windows 管理员权限，不受 Docker Desktop 的 GUI 问题影响。
坏处：会在你的 Ubuntu 里装约 200MB 包、开机不自启（每次要先 `service docker start`）。
**这条要你点头我才做**（会改动你的 WSL 环境）。

## 七、容器配置（✅ 已实测通过）

### 实测结果（2026-11-07 10:1x）

```
镜像：machdraw-agent:0.1   434 MB
容器：machdraw-agent       Up (healthy)   0.0.0.0:8078->8077/tcp

[OK] /api/health  chunks=566 docs=32 nodes=169 edges=279 tools=11 warn=[]
[OK] /api/figures figures=34
[OK] /api/pairs   pairs=10
[OK] /api/models  models=8
[OK] /api/modules modules=9
[OK] / 前端       200   含 #root
[OK] /admin 教师端 200   11094 bytes
[OK] /api/chat    23 帧 · 画布 ['three_view','evidence'] · token 13 段
```

### 两个构建期踩的坑

| 坑 | 现象 | 修法 |
|---|---|---|
| `# syntax=docker/dockerfile:1` | 要从死源拉 frontend 镜像 → EOF | 删掉该指令（本 Dockerfile 没用 BuildKit 专属语法） |
| 漏 `COPY apps/api/static` | 容器里 `/admin` 404 | Dockerfile 补一行 |
| 宿主机 8077 常被开发服务占用 | compose 起不来 | 端口改为 `${HOST_PORT:-8077}:8077`，用 `HOST_PORT=8078 docker compose up -d` |

### 怎么用

```powershell
# 构建 + 启动（推荐 8078，避开本机开发服务）
$env:HOST_PORT="8078"; docker compose up -d --build

# 看状态 / 日志
docker compose ps
docker compose logs -f --tail 30

# 停掉
docker compose down          # 数据卷 ./data-docker 保留
```

打开 <http://127.0.0.1:8078/>（学生端）与 <http://127.0.0.1:8078/admin>（教师端）。

### 容器里装了什么

| 内容 | 说明 |
|---|---|
| 前端构建产物 | 阶段 1 由 `node:22-alpine` 构建，单包 ~392KB（gzip 123KB） |
| FastAPI 后端 | `python:3.12-slim` + fastapi/uvicorn/pydantic/numpy/jieba |
| 知识库 + 预建索引 | 构建期跑 `pipeline/build_kb.py`（566 块，约 1.7 秒） |
| 教师端静态页 | `apps/api/static/admin.html` |
| 数据卷 | `/app/data` → 宿主 `./data-docker`（SQLite：账号/会话/错题/埋点） |

### 原始配置参考（保留）

| 文件 | 内容 |
|---|---|
| `Dockerfile` | 多阶段：`node:22-alpine` 构建前端 → `python:3.12-slim` 运行时 + 构建期预建检索索引 + HEALTHCHECK |
| `docker-compose.yml` | 8077 端口、`./data-docker:/app/data` 持久化卷、可用环境变量注入 LLM Key |
| `.dockerignore` | 排除 `node_modules / .venv / data / _recon / 参考内容（227MB）` 等 |
| `apps/api/requirements.txt` | fastapi / uvicorn[standard] / pydantic / numpy / jieba |

一旦引擎起来，`docker compose up -d --build` 即可，我会顺手验证：
`/api/health` 返回、`/` 前端可开、`/admin` 可开、问一句话能出证据卡。
