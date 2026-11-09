# 18 · 继续尝试：OCR 增强 / RapidOCR 实测 / 学习数据备份恢复

> 接 [17](17-第三轮-语音深色移动端OCR持久化.md) 的两条"仍然受限"：
> ① OCR 只用了 tesseract（手写/公式不稳）；② Render 免费档没有持久化。
> 这轮尝试了 RapidOCR，并把"持久化"补成可跨设备迁移的备份/恢复。

---

## 1. OCR 增强（tesseract 路线，已上线）

`POST /api/vision/ocr` 重写为：

1. **预处理**：灰度化 → `ImageOps.autocontrast` → 小图（宽 <1000）2× LANCZOS 放大 → 最大边限 2200；
2. **识别**：`--psm 6`（统一文本块，适合拍题）；
3. **后处理** `_normalize_ocr_text()`：
   - 去掉中文字符之间的空格（tesseract 典型输出）；
   - 标点两侧空格清理；
   - `k eff / k-eff` → `k_eff`，`rho` → `ρ`，`pcm` 统一小写；
   - 合并 3 个以上连续空行。

实测（900×320 的题目截图）：

```
7. 反应性方程: ρ = (k_eff - 1) /k_eff
已知 k_eff=1.05，求反应性是多少 pcm?
A. 4762 pcm B. 5000 pcm
```

比旧输出（`反 应 性 方 程 : rho = (k eff - 1) /k eff`）可读性明显提升。

## 2. RapidOCR 尝试与结论（未默认启用）

- 本地实测 `rapidocr-onnxruntime 1.4.4`：识别几乎无空格、`k_eff` 正确，耗时约 2.5s（初始化 1s）；
- 内存：**峰值约 310MB**（onnxruntime + 检测/识别模型），空载工作集约 112MB；
- 部署到 Render 免费 512MB 实例后，OCR 请求直接 **502，服务被 OOM 杀掉**；已回滚：
  - 环境变量 `RP_OCR_ENGINE=tesseract`；
  - `requirements.txt` 不再默认安装 RapidOCR；
  - 新增可选文件 `apps/api/requirements-ocr-rapid.txt`（附系统依赖与内存说明），供 ≥1GB 实例/本地使用；
  - 代码保留 `RP_OCR_ENGINE=rapid` 分支，失败会自动回落 tesseract。

结论：**免费档内存不够跑 RapidOCR**。想要更好的拍题体验，需要：
- Render Starter（或更大内存）+ `RP_OCR_ENGINE=rapid`；或
- 外接 OCR 服务/多模态模型；或
- 用 PaddleOCR 但同样需要更大内存。

## 3. 学习数据备份 / 恢复（跨设备）

新增：

- `GET /api/backup`：返回当前账号的 `mastery / wrongbook / records`（+ 导出时间）；
- `POST /api/restore`：**只增不减**——掌握度按 `last_at` 取新、错题本按 `题面 + trace_ref` 去重、records 合并；
- 前端 `lib/backup.ts`：导出时把服务端数据 + 浏览器里的 `sessions/mastery` 镜像一起打包成 JSON；导入时先 POST restore，再写回 localStorage，刷新后生效；
- 入口：顶栏「历史」抽屉底部「导出备份 / 导入备份」。
- 效果：换电脑/换浏览器/重装系统前导出，导入后掌握度与错题本可以带走；会话也会随备份恢复。

## 4. 顺手修的一个真 bug

`/api/mastery/report` 在加 `_apply_mastery()` 辅助函数时，装饰器被错误地加在了辅助函数上，导致：
- 路由实际绑到了 `_apply_mastery`，请求返回 422（`st/account/signal` 被当成 query 参数）；
- 判分接口（直接调辅助函数）正常，所以之前没暴露。

已删除重复的 `@app.post("/api/mastery/report")`，实测 report/backup/restore 均正常。

## 5. 验证

- 本地：
  - OCR 输出见上；`engine=tesseract`；
  - `report` → 0.35/在学；`backup` 返回 mastery/wrongbook/records；`restore` 到新账号 `imported_mastery=1`；
  - 锚点 68/68、smoke 27/27。
- 线上：
  - `RP_OCR_ENGINE=rapid` 时 502（OOM）→ 已改回 `tesseract`；
  - 部署后 `/api/vision/ocr` 正常返回归一化文本；`/api/backup`、`/api/restore` 可用；健康检查仍为星火。

## 6. 仍然没解决的

| 项 | 现状 / 建议 |
|---|---|
| 手写/复杂公式 | tesseract 能力上限；要质变需更大内存跑 RapidOCR/PaddleOCR 或接多模态 |
| 真正持久化 | 备份/恢复是"手动搬家"；跨设备自动同步仍需 Postgres/Supabase（或付费 Render Disk） |
| 自动备份 | 现在要手动点导出；可加"每周自动下载备份"提醒 |
| 公式结构化 | OCR 只出文本，不解析 LaTeX；后续可接 mathpix 类服务或公式识别模型 |

---

相关文件：

- 后端：`api/app/main.py`（OCR/备份/恢复）、`requirements.txt`、`requirements-ocr-rapid.txt`、`Dockerfile`
- 前端：`lib/{backup.ts,api.ts}`、`shell/HistoryDrawer.tsx`、`shell/Composer.tsx`（相机 capture）、`app.css`
