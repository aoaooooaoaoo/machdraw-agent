"""生成《核反应堆物理 AI 助教 · 图文使用说明》HTML（图片内嵌 base64，可打印/转 PDF）。

用法：D:\\python\\python.exe scripts/gen_manual_html.py
输出：docs/22-使用说明-图文版.html
"""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "_manual_assets"
OUT = ROOT / "docs" / "22-使用说明-图文版.html"


def img(name: str, caption: str, cls: str = "") -> str:
    p = ASSETS / name
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"""
    <figure class="{cls}">
      <img src="data:image/jpeg;base64,{b64}" alt="{caption}" />
      <figcaption>{caption}</figcaption>
    </figure>"""


def table(headers, rows):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


CSS = """
:root { --blue:#1d4ed8; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --soft:#f8fafc; }
* { box-sizing: border-box; }
body { margin:0; font-family:"Microsoft YaHei","PingFang SC","Noto Sans SC",sans-serif;
       color:var(--ink); font-size:10.5pt; line-height:1.65; background:#eef2f7; }
.page { width:210mm; min-height:297mm; padding:18mm 18mm 16mm; margin:0 auto 10mm;
        background:#fff; box-shadow:0 8px 24px rgba(15,23,42,.08); page-break-after:always; }
.page:last-child { page-break-after:auto; }
h1 { font-size:20pt; color:var(--blue); margin:0 0 4mm; padding-bottom:2mm; border-bottom:2px solid var(--blue); }
h2 { font-size:13pt; margin:6mm 0 2mm; }
p { margin:0 0 3mm; }
ul,ol { margin:0 0 3mm; padding-left:6mm; }
li { margin:1mm 0; }
.small { font-size:9.5pt; color:var(--muted); }
.cover { display:flex; flex-direction:column; justify-content:center; min-height:260mm; text-align:center; }
.cover .kicker { color:var(--blue); font-size:12pt; letter-spacing:.3em; }
.cover h1 { border:none; font-size:30pt; margin:8mm 0 2mm; }
.cover .sub { font-size:16pt; color:var(--ink); }
.cover .meta { margin-top:20mm; color:var(--muted); font-size:10pt; line-height:2; }
.cover .meta b { color:var(--ink); }
figure { margin:4mm 0 5mm; text-align:center; page-break-inside:avoid; }
figure img { max-width:100%; border:1px solid var(--line); border-radius:2mm; }
figure.narrow img { width:62%; }
figcaption { font-size:9pt; color:var(--muted); margin-top:1.5mm; }
table { width:100%; border-collapse:collapse; margin:3mm 0 5mm; font-size:9.5pt; page-break-inside:avoid; }
th { background:var(--blue); color:#fff; padding:2.2mm 2.5mm; text-align:left; }
td { border:1px solid var(--line); padding:2mm 2.5mm; vertical-align:top; }
tr:nth-child(even) td { background:var(--soft); }
.note { background:#fff7ed; border-left:4px solid #f59e0b; padding:3mm 4mm; margin:3mm 0; border-radius:0 2mm 2mm 0; }
.tip { background:#eff6ff; border-left:4px solid var(--blue); padding:3mm 4mm; margin:3mm 0; border-radius:0 2mm 2mm 0; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:4mm; }
kbd { font-family:Consolas,monospace; font-size:9pt; border:1px solid #cbd5e1; border-bottom-width:2px;
      border-radius:1mm; padding:.5mm 1.5mm; background:#f8fafc; }
@media print {
  body { background:#fff; }
  .page { width:auto; min-height:auto; margin:0; padding:0; box-shadow:none; }
  @page { size:A4; margin:16mm 16mm 14mm; }
}
"""


def build() -> str:
    parts: list[str] = []
    parts.append(f"<style>{CSS}</style>")

    # 封面
    parts.append(
        f"""
    <section class="page cover">
      <div class="kicker">COURSE AI ASSISTANT</div>
      <h1>核反应堆物理 AI 助教</h1>
      <div class="sub">图 文 使 用 说 明</div>
      <div class="meta">
        在线地址：<b>https://reactor-physics-agent.onrender.com/</b><br/>
        教师端：<b>https://reactor-physics-agent.onrender.com/admin</b><br/>
        版本：v1.0 · 2026-11-10
      </div>
      <div class="small" style="margin-top:24mm">学生 / 教师手册 · 10 个模块 · 8 类画布 · 可溯源 · 可计算</div>
    </section>"""
    )

    # 1
    parts.append(
        f"""
    <section class="page">
      <h1>1. 快速开始</h1>
      <p>打开在线地址，输入学号/姓名作为账号、任意密码，点「进入工作台」。首次输入会自动建号；之后用同一账号+密码找回个人记录。</p>
      {img("workbench.jpg", "图 1 工作台总览：①顶栏 ②模块导航 ③对话与公式 ④画布（证据卡） ⑤输入框")}
      <ul>
        <li><b>① 顶栏</b>：连接状态、当前模型、笔记、历史、复习、搜索（命令面板）、主题、反馈。</li>
        <li><b>② 左栏</b>：10 个模块导航 + 知识库统计 + 门控阈值 τ=0.40。</li>
        <li><b>③ 对话</b>：消息、思考过程、工具卡、Markdown 与 KaTeX 公式。</li>
        <li><b>④ 画布</b>：证据卡 / 计算卡 / 曲线 / 对比 / 批注 / 题卡 / 错题本 / 知识图谱。</li>
        <li><b>⑤ 输入框</b>：Enter 发送、Shift+Enter 换行；左侧可新会话、语音、拍题。</li>
      </ul>
      <div class="tip">不确定从哪开始？按 <kbd>Ctrl/⌘ + K</kbd> 打开命令面板，搜模块或问题。</div>
    </section>"""
    )

    # 2
    parts.append(
        f"""
    <section class="page">
      <h1>2. 提问、证据与公式</h1>
      <p>直接用自然语言提问。回答上方的「工具卡」显示调用了什么工具；右栏每段证据带「文档 · 章节 · chunk_id · 相关度」，可展开全文或围绕此段追问。</p>
      {table(["想做什么", "这样问", "会得到"], [
          ["问概念", "什么是缓发中子？为什么它对反应堆控制很重要？", "回答 + 证据卡 + 公式 + 出处"],
          ["算题", "k_eff=1.05 时反应性是多少 pcm？", "计算卡：输入 / 步骤 / 结果"],
          ["刷题", "考我一道题", "题卡：先自己想 → 看解析 → 判分"],
          ["查关系", "点堆动力学依赖哪些前置知识？", "知识图谱 / 前置关系"],
      ])}
      <div class="note">出现「知识库未收录」不是系统错误，而是检索覆盖率低于门控阈值 τ=0.40 时的<b>主动拒答</b>。换课程里的术语再问即可（如有效增殖系数、缓发中子、多普勒展宽、氙中毒）。</div>
      <p>公式会自动排版：回答里用 LaTeX（行内 <code>$...$</code>、行间 <code>$$...$$</code>），页面渲染成分式。</p>
    </section>"""
    )

    # 3
    parts.append(
        f"""
    <section class="page">
      <h1>3. 10 个模块速查</h1>
      {table(["模块", "适合问什么", "主要产出"], [
          ["全局对话", "不确定归哪类的问题", "自动路由 + 证据/计算"],
          ["教材与概念溯源", "定义、原理、教材原文", "证据卡 + 出处"],
          ["临界与扩散计算", "k∞、M²、B²、临界尺寸、反射层", "计算卡（确定性引擎）"],
          ["动力学与反应性", "缓发中子、周期、瞬发临界、$ 换算", "曲线 + 计算卡"],
          ["燃耗与中毒", "氙/钐中毒、碘坑、燃耗深度", "曲线 + 计算卡"],
          ["概念辨析", "快/热群、扩散/输运、温度系数", "对比表 + 随堂题"],
          ["知识图谱", "前置关系、易混淆、学习路径", "星图 + 焦点关系"],
          ["学习计划", "今天学什么、复习什么", "今日任务 + 下一步建议"],
          ["错题与计算批改", "错题六步诊改、错题本", "批注 + 错题本"],
          ["费曼追问", "用自己的话讲一遍", "多轮追问 + 评价"],
      ])}
      <p class="small">提示：模块不是越多越好；概念题走「教材溯源」，数值题走「计算」，练习走「概念辨析/错题」，不知道走「全局对话」。</p>
    </section>"""
    )

    # 4 图谱
    parts.append(
        f"""
    <section class="page">
      <h1>4. 知识图谱</h1>
      <p>左栏「知识图谱」打开十章彩色星图：节点颜色=章节，节点大小=关联数，中心点=学习状态（未学 / 在学 / 已掌握 / 需复习）。</p>
      {img("graph.jpg", "图 2 知识图谱：按章分簇的星图，可搜索、缩放、点节点看详情")}
      <ul>
        <li>搜索框可搜知识点或 kp_id；点章名 pill 聚焦该章。</li>
        <li>悬停高亮一跳邻居；点节点看定义、要点、易错、前置/后继。</li>
        <li>层级 L1–L4 与章筛选可隐藏；可切「浅色/星图」主题。</li>
      </ul>
    </section>"""
    )

    # 5 刷题
    parts.append(
        f"""
    <section class="page">
      <h1>5. 刷题、判分与掌握度</h1>
      <p>输入「考我一道题」，或在概念辨析/错题模块里出题。题卡先自己想 →「我先想想」看解析 →「自动判分」或自评「我会了 / 还不会」。</p>
      {img("quiz.jpg", "图 3 题卡自动判分：分数 / 评语 / 漏掉的点 / 参考答案，并回写掌握度")}
      <ul>
        <li>自动判分：星火对照参考答案给分，约 10–15 秒；不及格自动进错题本。</li>
        <li>自评：展开解析后点「我会了 / 还不会」，同样回写掌握度。</li>
        <li>掌握度变化会同步到知识图谱节点颜色与学习计划。</li>
      </ul>
    </section>"""
    )

    # 6 学习计划
    parts.append(
        f"""
    <section class="page">
      <h1>6. 学习计划</h1>
      <p>左栏「学习计划」按掌握度、到期复习和前置依赖安排今天学什么。</p>
      {img("study.jpg", "图 4 学习计划：今日任务、下一步建议、掌握度统计与快捷入口")}
      <ul>
        <li><b>今日任务</b>：到期复习（需复习 1 天 / &lt;75% 3 天 / ≥75% 7 天）。</li>
        <li><b>下一步建议</b>：按图谱前置关系推荐「前置已掌握」的知识点。</li>
        <li>点「去复习 / 去学习」自动切到对应模块并发起提问。</li>
      </ul>
    </section>"""
    )

    # 7 便签+历史+命令
    parts.append(
        f"""
    <section class="page">
      <h1>7. 便签、历史与命令面板</h1>
      <p>顶栏「笔记」打开可拖拽便签：拖动标题栏移动，支持多张、颜色、折叠、Markdown/公式预览，按账号自动保存。</p>
      {img("sticky.jpg", "图 5 可拖拽便签：随手记录，自动保存", "narrow")}
      <p>顶栏「历史」按天保存会话，点一条恢复消息 + 最近画布；「复习」打开到期复习抽屉。</p>
      {img("palette.jpg", "图 6 命令面板（Ctrl/⌘ + K）：搜索模块 / 提问 / 操作")}
      <div class="tip">快捷键：<kbd>Ctrl/⌘ + K</kbd> 命令面板，<kbd>Ctrl/⌘ + /</kbd> 聚焦输入框，<kbd>Esc</kbd> 关闭浮层。</div>
    </section>"""
    )

    # 8 语音拍照 + 手机
    parts.append(
        f"""
    <section class="page">
      <h1>8. 语音、拍照与手机端</h1>
      <ul>
        <li><b>语音输入</b>：输入框麦克风（Chrome/Edge，需麦克风权限），识别结果进入草稿。</li>
        <li><b>朗读</b>：助手消息操作条「朗读 / 停止」。</li>
        <li><b>拍题</b>：输入框回形针 → 选图/拍照，发送时自动 OCR；印刷体效果好，手写/复杂公式有限。</li>
        <li><b>导出</b>：画布右上「导出 Markdown」「打印 / 另存 PDF」。</li>
      </ul>
      <p>手机浏览器打开同一网址即可：底部固定「模块 / 对话 / 画布 / 图谱」，左栏变抽屉；可「添加到主屏幕」全屏打开（无离线缓存）。</p>
      {img("mobile.jpg", "图 7 手机端：底部导航 + 对话 + 画布", "narrow")}
    </section>"""
    )

    # 9 教师 + 数据 + FAQ
    parts.append(
        f"""
    <section class="page">
      <h1>9. 教师端与数据备份</h1>
      <h2>教师端 /admin</h2>
      <p>可看：语料与图谱规模、账号与消息、拒答率/覆盖率、错题根因、学习者模型（各状态人数 + 最需要关注的知识点）、语料清单、待复核段落、账号列表。</p>
      <div class="note">教师端目前没有单独登录鉴权，仅限内部教学使用；公网正式开课建议加访问控制。</div>
      <h2>数据备份与恢复（重要）</h2>
      <p>对话、画布、便签、掌握度镜像会自动保存在当前浏览器；但服务器是 Render 免费档，重启/重部署会清空服务端数据（账号、历史、掌握度、错题本服务端部分）。</p>
      <ul>
        <li>换设备或重启前：顶栏「历史」→ 底部「导出备份」（JSON）。</li>
        <li>新设备/恢复：同一位置「导入备份」，刷新后生效。</li>
        <li>备份只增不减；错题按题面+trace 去重。建议每周导出一次。</li>
      </ul>
    </section>"""
    )

    # 10 FAQ
    parts.append(
        f"""
    <section class="page">
      <h1>10. 快捷键与常见问题</h1>
      {table(["快捷键", "作用"], [
          ["Enter", "发送"],
          ["Shift + Enter", "换行"],
          ["Ctrl/⌘ + K", "命令面板"],
          ["Ctrl/⌘ + /", "聚焦输入框"],
          ["Esc", "关闭命令面板 / 历史 / 复习 / 便签"],
      ])}
      <h2>常见问题</h2>
      <p><b>Q：回答为什么慢？</b><br/>星火首答约 10–18 秒；相同问题会命中缓存；计算/出题通常毫秒级。</p>
      <p><b>Q：公式不渲染？</b><br/>点「重新回答」；系统已要求模型用 $...$ / $$...$$。</p>
      <p><b>Q：拍题不准？</b><br/>拍正、清晰、光线均匀，或补一句文字描述。</p>
      <p><b>Q：数据丢了？</b><br/>有备份就导入；没备份则免费档重启后无法找回。</p>
      <p><b>Q：能离线用吗？</b><br/>不能，需要联网访问；本地部署可完全离线（见 DEPLOY.md）。</p>
      <h2>已知限制（如实说）</h2>
      <ul>
        <li>Render 免费档：15 分钟闲置休眠、无持久盘（数据会重置）。</li>
        <li>只有 Spark 文本模型，无多模态视觉；拍题靠 tesseract OCR。</li>
        <li>自动判分约 10–15 秒；复杂主观题建议对照参考答案。</li>
        <li>历史/掌握度/便签跨设备不同步（靠导出/导入）。</li>
      </ul>
      <p class="small">完整文字版见 docs/21-使用说明.md；功能以线上实际页面为准。</p>
    </section>"""
    )

    return f"<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'/><title>核反应堆物理 AI 助教 · 图文使用说明</title></head><body>{''.join(parts)}</body></html>"


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print("saved", OUT, OUT.stat().st_size)
