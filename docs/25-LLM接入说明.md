# 25 · 大模型接入说明（provider / key / 排错）

> 本项目**默认不需要任何 API Key**：`MW_LLM_PROVIDER=mock` 时走「本地证据抽取 + 模板组织」，
> 检索、门控、数值引擎全部照常工作，只是语言组织由模板完成。
> 想接真模型时按下表配置，**代码不需要改**（`llm.py` 是标准 OpenAI 协议）。

---

## 一、当前状态

| 环境 | provider | 说明 |
|---|---|---|
| 本地（8077） | `mock` | 无需 key，回答 0.3 秒 |
| 线上（Render） | `mock` | `render.yaml` 里固定 `MW_LLM_PROVIDER=mock` |
| 参考作品线上 | `deepseek-flash` | 它在 Render 控制台填了真 key（源码包里的 key 是占位符） |

---

## 二、支持的供应商（都是 OpenAI 兼容协议）

| provider 取值 | base_url | 模型示例 | 备注 |
|---|---|---|---|
| `mock` | — | — | 默认，无需 key |
| `openai-compatible` | `https://maas-api.cn-huabei-1.xf-yun.com/v2` | `spark-x2.6` / `spark-x2.5` / `spark-x2.5-4b` | **讯飞星辰 MaaS**，key 形如 `ak-xxxx`，端点带 `/v2` |
| `openai-compatible` | `https://spark-api-open.xf-yun.com/v1` | `lite`（免费）/ `generalv3.5` / `4.0Ultra` | **讯飞星火老 HTTP 接口**，凭据叫 APIPassword，需先在控制台领额度 |
| `deepseek` | `https://api.deepseek.com/v1` | `deepseek-chat` | 参考作品用的（它写的是 `deepseek-flash`） |
| `openai-compatible` | `http://127.0.0.1:11434/v1` | `qwen2.5:3b` | **本地 Ollama**，纯 CPU 可跑，key 随便填 `ollama` |

> ⚠️ 代码里有一条硬逻辑：`provider != mock` 但 **`MW_LLM_API_KEY` 为空时强制回落 mock**。
> 所以本地 Ollama 也要填一个占位 key（`ollama` 即可），否则不会走真模型。

---

## 三、环境变量

```
MW_LLM_PROVIDER   mock | deepseek | openai-compatible
MW_LLM_BASE_URL   OpenAI 兼容端点（不含 /chat/completions）
MW_LLM_MODEL      模型名
MW_LLM_API_KEY    key（也兼容 DEEPSEEK_API_KEY 这个名字）
```

本地：`apps/api/.env`（已被 `.gitignore` 排除，不会进仓库）
线上：Render 控制台 → 服务 → Environment，改完自动重新部署

---

## 四、先跑诊断，别盲配

```powershell
python scripts\check_llm.py            # 打印当前配置 + 真实调用一次
python scripts\check_llm.py --list     # 只看配置
```

它会自动翻译常见错误码：

| 错误码 | 含义 | 怎么办 |
|---|---|---|
| 401 `invalid user` | key 无效 | 检查是否复制完整 |
| 11200 | 账号没有该模型的有效订单/额度 | 去对应平台开通/领额度 |
| 11201 | 日流控超限 | 明天再用或换供应商 |
| 11202 / 11203 | 秒级 / 并发流控 | 降并发 |
| 10013 / 10014 | 输入/输出内容审核不通过 | 换问法 |
| 10404 | 模型名不存在（MaaS） | 用 `spark-x2.6` 这类准确名字 |

---

## 五、踩过的坑（真实记录）

1. **`ak-` 开头的 key 不是老星火接口的凭据。**
   老接口（`spark-api-open.xf-yun.com/v1`）要的是控制台里的 **APIPassword**；
   `ak-` 是**星辰 MaaS 平台**的 key，端点必须是 `https://maas-api.cn-huabei-1.xf-yun.com/v2`，
   模型名是 `spark-x2.6` 这类。用错端点会得到 `11200 AppIdNoAuthError`。
2. **平台之间的"免费"不一样**：星火老接口的 `lite` 免费但要在 `console.xfyun.cn` 领额度；
   MaaS 的 `spark-x2.5-4b` 标称免费但也要在 `maas.xfyun.cn` 开通订单，否则同样 11200。
3. **请求体带 BOM 会报 10003 invalid data。** PowerShell 5.1 的 `Set-Content -Encoding UTF8`
   会加 BOM，用 curl 的 `--data @file` 发出去就废了。用 Python 写文件时不带 BOM。
4. **模型名会下线**：参考作品的注释里写着「`deepseek-chat` 已不在模型列表里，别再写回来」。
   接第三方模型前先跑一次诊断脚本，别靠记忆。

---

## 六、配好之后怎么验证

```powershell
# 1. 诊断能通
python scripts\check_llm.py

# 2. 起服务，问一句，看状态栏 provider 变成真模型
#    顶栏不再显示 mock(extractive-local)
# 3. 看回答里有没有"模型调用失败，已自动降级"的提示（有就是没接上）
```

代码带降级：调用失败会自动回落 mock 并在回答末尾注明，**不会中断对话**。

---

## 七、线上还缺什么

Render 免费档 512 MB 内存，**跑不了本地模型**（3B 模型至少要 2–3 GB）。
线上只能是「云 API」或「mock」。本地模型只在你自己电脑上跑（见第二节 Ollama 一行）。


---

## 八、实测：讯飞星辰 MaaS 免费模型（2026-11-07）

### 8.1 真正可用的免费型号

| 型号 | 价格 | 说明 |
|---|---|---|
| `spark-x2.6-4b` | **¥0/百万 tokens** | 限时免费，带思维链 |
| `spark-x2.5-4b` | **¥0/百万 tokens** | 限时免费，带思维链 |

> ⚠️ 平台内「模型体验」能用 ≠ API 能用。API 还需要：
> ① 在「API Key 管理 → 授权管理」给 key 勾选模型（默认 **0 个**，不勾就是 11200）；
> ② 该模型有生效的后付费订单（¥0 也要"后付费服务生效中"，见「模型服务 → API调用」弹窗）。

### 8.2 ★ 关掉思维链：115 秒 → 5.7 秒

同一个问题（"什么是尺寸基准？…"）实测：

| 配置 | 耗时 | 推理 token | 总 token |
|---|---|---|---|
| `spark-x2.6-4b` 默认 | **115.3 s** | 3405 | 3880 |
| `spark-x2.5-4b` 默认 | 22.7 s | 1243 | 1717 |
| `spark-x2.6-4b` + `thinking:{"type":"disabled"}` | **5.7 s** | **0** | 495 |
| `spark-x2.6-4b` + `enable_thinking:false` | 5.7 s | 0 | 471 |
| `spark-x2.6-4b` + `reasoning_effort:"none"` | 6.4 s | 0 | 565 |
| `spark-x2.6-4b` + `reasoning_effort:"low"` | 17.2 s | 1031 | 1374 |

**结论**：这些 4B 模型默认会先生成一大段中文思维链（reasoning_content），
对"依据证据组织一段回答"这种任务完全是浪费。关掉后**快 20 倍、省 87% token，回答还更长**。

配置方式（`config.py` 已支持）：

```
MW_LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}
```

代码里是通用透传：`_http_chat` 会把这段 JSON 合并进请求体，
换任何供应商/模型都能用它传额外参数。

### 8.3 本地实测

```
/api/health → provider=openai-compatible  model=spark-x2.6-4b  has_key=True
问：什么是尺寸基准？为什么同一方向的定位尺寸要从同一基准出发？
  → 6.9 s，42 帧，回答带「证据1/2/3」引用 + 5 处出处
```

对比 mock 模式：同样问题 0.3 s，但回答是模板拼装的，没有这种论证结构。


---

## 九、最终落地配置（2026-11-07 晚上，本地 + 线上都跑通）

### 9.1 本地 `apps/api/.env`（已在 .gitignore）

```
MW_LLM_PROVIDER=openai-compatible
MW_LLM_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2
MW_LLM_MODEL=spark-x2.6-4b
MW_LLM_API_KEY=ak-****
MW_LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}
```

### 9.2 线上 Render

- **`render.yaml` 里声明**（进仓库，非机密）：PROVIDER / BASE_URL / MODEL / EXTRA_BODY
- **控制台里填**（不进仓库）：`MW_LLM_API_KEY`，用「Environment → Edit → Add variable」加
- 实测：改完自动重新部署，`/api/health` 变 `provider=openai-compatible · model=spark-x2.6-4b · llm_ready=true`

### 9.3 实测结果

| 环境 | 提问 | 耗时 | 表现 |
|---|---|---|---|
| 本地 | 为什么同一方向的定位尺寸要从同一基准出发？ | 6.9 s | 带「证据1/2/3」引用 + 5 处出处 |
| 线上 | 同上 | 8.3 s | 分三点论证，每点带出处 |
| 线上 | 剖视图和断面图有什么区别？ | 0.1 s | 走确定性工具（成对图），不经过模型 |
| 线上 | Φ30 H7/k6 是什么配合？ | 0.1 s | 走公差引擎，数值由 GB/T 1800 查表 |

> **注意区分**：「走工具的题」永远 0.1 秒且数值绝对准确（引擎算）；
> 「概念解释题」才走模型（5–9 秒）。这是设计使然：**能算的绝不让模型背**。

### 9.4 顺手修掉的一个真 bug

`/api/health` 的 `has_key` 原来写成 `bool(LLM_PROVIDER != "mock")` —— **只看 provider 不看 key**。
后果：线上 provider 配了但没有 key 时，状态显示"有 key"，而 `generate()` 悄悄回落 mock
且**不打降级提示**（因为走的是"未配置"分支，不是"调用失败"分支）。
已改成 `bool(LLM_API_KEY)`，并新增 `llm_ready = provider != mock and 有 key`。

### 9.5 费用与额度

`spark-x2.6-4b` 是 **¥0/百万 tokens**，TPM 上限 100 万。
公开站点被人随便用也不花钱，只是可能触发速流控（11202/11203）。
」
