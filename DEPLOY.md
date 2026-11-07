# 部署到公网（Render，免费档）

## ✅ 已上线

**线上地址：<https://machdraw-agent.onrender.com>**

| 项 | 值 |
|---|---|
| 托管 | Render（Free 档，Docker 运行时，Oregon 区域） |
| 代码仓库 | <https://github.com/aoaooooaoaoo/machdraw-agent> |
| 部署方式 | Blueprint（读仓库根的 `render.yaml`），改代码 push 后自动重新部署 |
| 实测 | `/api/health` → 566 块 / 32 文档 / 169 节点 / 279 边 / 11 工具，0 告警 |
| 实测 | 前端登录 → 知识图谱整页 169 节点渲染 → 提问「Φ30 H7/k6」→ 工具卡 + 6 段证据 + 100% 覆盖率 + 26 帧 SSE |
| 账号 | 任意账号首次输入即自动创建（线上数据库独立于本地） |

> ⚠️ 免费档 15 分钟无访问会休眠。**休眠后第一次打开要等约 40 秒**（页面显示 loading），
> 之后正常。这是免费档的固有行为，参考作品现在也是这个状态。
>
> ⚠️ 免费档没有持久磁盘：账号、错题、会话记录**每次重新部署/重启会清空**。
> 演示够用，正式教学需要升级付费档（$7/月）或外接数据库。

---


> 目标：像参考作品 `https://materials-lab-agent.onrender.com/` 那样，得到一个
> **任意电脑打开就能用的固定链接**。
> 现状：**代码侧我已全部准备好**，只剩两个账号需要你本人注册（要邮箱验证）。

---

## 一、我已经准备好的

| 项 | 状态 |
|---|---|
| `Dockerfile` | ✅ 改成跟随平台注入的 `$PORT`（原来写死 8077，Render 会连不上） |
| `render.yaml` | ✅ 蓝图：`runtime: docker`、`plan: free`、健康检查 `/api/health` |
| `.gitignore` | ✅ 排除 `参考内容/`(705MB)、`_recon/`(732MB)、`node_modules`、`.venv`、`data/index` |
| `.gitattributes` | ✅ Dockerfile/yml 强制 LF（`HEALTHCHECK` 的续行遇到 CRLF 会坏） |
| 本地 git 仓库 | ✅ 已 `git init` + 首次提交，**402 个文件**（没有大目录误入） |
| 部署 SSH 公钥 | ✅ 已生成，见下 |

理论入库体积：**约 16 MB**（远低于 GitHub 限制）。

---

## 二、只有你能做的两件事

### 第 1 步：注册 GitHub（约 2 分钟）

1. 打开 <https://github.com/signup>
2. 填邮箱 → 设置密码 → 用户名
3. **去邮箱点验证链接**
4. 回来点右上角头像 → **Settings** → 左侧 **SSH and GPG keys** → **New SSH key**
   - Title 随便填：`machdraw-deploy`
   - Key 粘贴下面这行（**公钥，泄露无害**）：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHCSTgRkTkzHqiMN4YnIqxDLeex9zsQQXAlt/G0iO/ez machdraw-deploy
```

5. 新建仓库：右上 **+** → **New repository** → 名字填 `machdraw-agent` → **Private 或 Public 都行** → 不要勾选初始化 README → **Create**

> 建完把仓库地址（形如 `git@github.com:你的用户名/machdraw-agent.git`）告诉我，我来推送。

### 第 2 步：注册 Render（约 1 分钟，用 GitHub 一键登录）

1. 打开 <https://dashboard.render.com/register>
2. 选 **GitHub** 登录（不用再填邮箱）
3. 授权 Render 读取仓库（可以只授权 `machdraw-agent` 这一个）

> 这一步之后我可以直接帮你点「New → Blueprint → 选仓库 → Apply」。

---

## 三、然后我来做（约 6 分钟）

```powershell
# 1. 把仓库推到 GitHub（用你刚加的 SSH key）
git remote add origin git@github.com:<你的用户名>/machdraw-agent.git
git push -u origin main

# 2. Render 上 New → Blueprint → 选 machdraw-agent → Apply
#    它读 render.yaml：Docker 构建 + 免费档 + 健康检查 /api/health

# 3. 等构建（5–8 分钟：装 node 依赖 + Python 依赖 + 建检索索引）

# 4. 拿到固定链接 https://machdraw-agent-xxxx.onrender.com
```

---

## 四、免费档的真相（必须提前知道）

| 项 | 实际情况 | 影响 |
|---|---|---|
| **休眠** | 15 分钟无人访问就休眠 | 下次打开要等 **约 40 秒**（页面显示 "Application loading"，参考作品现在也是这个状态） |
| **内存** | 512 MB | 我们实测运行时约 250–300 MB，够用；但不能再开大模型本地推理 |
| **CPU** | 0.1 核 | 检索/建索引慢 5–10 倍，冷启动更明显 |
| **持久化磁盘** | 免费档**没有** | SQLite 里的账号/错题/会话**每次重启会清空**；项目交付演示够用，正式教学要升级或换 Postgres |
| **额度** | 750 小时/月 | 单个服务常年在线够用（一个月 720 小时） |
| **地域** | 建议选 Singapore / Oregon | Singapore 从国内访问更快 |

> 如果将来要「不睡 + 有持久盘」，付费档 $7/月即可；或换到你自己的云服务器（Docker 镜像直接跑）。

---

## 五、备用方案（Render 走不通时）

| 方案 | 免费？ | 固定链接 | 代价 |
|---|---|---|---|
| **Cloudflare Tunnel** | ✅ | ❌ 每次随机，除非有域名 | 你电脑必须开机 |
| **Hugging Face Spaces** | ✅ | ✅ | ⚠️ 我实测**你这网络打不开 huggingface.co**（超时），不适合 |
| **自己的云服务器** | ❌ | ✅ | 需要买机器，Docker 镜像可直接跑 |
| **离线 ZIP / 镜像** | ✅ | ❌ 不是链接 | 答辩现场最稳，不依赖网络 |

---

## 六、我验证过的事实

- ✅ 你网络能打开 `materials-lab-agent.onrender.com`（Render 域名可达，页面显示 "Application loading" 正在唤醒）
- ✅ GitHub 可达（HEAD 200，约 1.7 秒）
- ✅ 本地 Docker 镜像实测过：434 MB，容器 `Up (healthy)`，`/`、`/admin`、`/api/chat` 全通
- ❌ Hugging Face 不可达（超时）
- ⚠️ Docker Desktop 当前是停止状态，本地验证镜像前需要先打开它
