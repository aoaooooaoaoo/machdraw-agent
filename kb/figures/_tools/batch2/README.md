# batch2 —— 第二批 19 张教学图（FIG2-*）的生成源码

属于 `kb/figures/` 的**工具**，不是知识库内容，前端不读它、KB 构建也不扫它
（`apps/api/app/rag/chunking.py` 只扫 `kb/**/*.md`、`kb/knowledge/kp.jsonl`、`kb/exercises/*.jsonl`）。

## 怎么跑

```powershell
cd D:\桌面\机械制图agent
D:\python\python.exe kb\figures\_tools\batch2\build2.py            # 生成 SVG + 五项校验
D:\python\python.exe kb\figures\_tools\batch2\build2.py --prune    # 顺带删除被替换掉的旧 FIG2-*.svg
D:\python\python.exe kb\figures\_tools\batch2\preview2.py          # 内联成 HTML 供浏览器过目
```

`build2.py` 的安全设计：只写 `kb/figures/FIG2-*.svg`；写 `figures.jsonl` 时先保留所有非 `FIG2-` 行，
写前写后各算一次 sha256 复核（原有 15 行必须一字不变），并校验 figure_id 唯一、kp_id 真实存在、
图元数 6–40、无白色填充、每个 text 带 font-family。

## 各文件

| 文件 | 作用 |
|---|---|
| `fig2kit.py` | 复用上级目录的 `../svgkit.py`（只 import 不改），扩展椭圆、等测投影、表格、编号圆标 |
| `figs2_a.py` | 图 1–6：正等测、斜二测、圆的正等测、点/直线/平面的投影 |
| `figs2_b.py` | 图 7–12：圆柱截交线、相贯线简化、形体分析法、补画第三视图、尺寸基准 |
| `figs2_c.py` | 图 13–18：平键、滚动轴承、齿轮啮合、AutoCAD 界面、明细栏、读零件图 |
| `figs2_d.py` | 圆锥截交线（返工）：按解析几何求截交线并投影到锥面上，拆成 -1/-2 两张 |
| `catalog2.py` | 19 条目录（图号/章节/kp_id/图注），`figures.jsonl` 的唯一数据源 |
| `build2.py` | 生成 + 校验 + 安全追加 jsonl |
| `preview2.py` | 生成本地预览页（不写仓库，只写 `_tools/batch2/preview2.html`） |

> `preview2.html` 是内联预览页，跑一次就会生成，可随时删掉重生成，不是产物。
