"""生成《核反应堆物理 AI 助教 · 图文使用说明》DOCX。

用法：D:\\python\\python.exe scripts/gen_manual_docx.py
输出：docs/22-使用说明-图文版.docx
图片：docs/_manual_assets/*.jpg（由截图压缩而来）
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "_manual_assets"
OUT = ROOT / "docs" / "22-使用说明-图文版.docx"

BLUE = RGBColor(0x1D, 0x4E, 0xD8)
DARK = RGBColor(0x0F, 0x17, 0x2A)
GRAY = RGBColor(0x64, 0x74, 0x8B)
FONT = "微软雅黑"


def set_font(run, size=10.5, bold=False, color=None, font=FONT):
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def shade(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def bottom_border(paragraph, color="1D4ED8", size=8):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def h1(doc: Document, text: str):
    p = doc.add_heading(level=1)
    r = p.add_run(text)
    set_font(r, 16, True, BLUE)
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    bottom_border(p)
    return p


def h2(doc: Document, text: str):
    p = doc.add_heading(level=2)
    r = p.add_run(text)
    set_font(r, 12.5, True, DARK)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    return p


def para(doc: Document, text: str, size=10.5, color=DARK, bold=False, after=4):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_font(r, size, bold, color)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.35
    return p


def bullet(doc: Document, text: str):
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    set_font(r, 10.5, False, DARK)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.3
    return p


def image(doc: Document, name: str, caption: str, width=16.2):
    path = ASSETS / name
    if not path.exists():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(width))
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(caption)
    set_font(r, 9, False, GRAY)
    cap.paragraph_format.space_after = Pt(8)


def table(doc: Document, headers: list[str], rows: list[list[str]], widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        r = hdr[i].paragraphs[0].add_run(h)
        set_font(r, 9.5, True, RGBColor(0xFF, 0xFF, 0xFF))
        shade(hdr[i], "1D4ED8")
        hdr[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(val)
            set_font(r, 9, False, DARK)
            cells[i].paragraphs[0].paragraph_format.space_after = Pt(1)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def page_number(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r._r.append(fld)


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.8)
    page_number(sec)

    # ---------- 封面 ----------
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("核反应堆物理 AI 助教")
    set_font(r, 26, True, BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("图 文 使 用 说 明")
    set_font(r, 22, True, DARK)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("学生 / 教师手册 · v1.0")
    set_font(r, 12, False, GRAY)

    for _ in range(3):
        doc.add_paragraph()
    info = [
        ("在线地址", "https://reactor-physics-agent.onrender.com/"),
        ("教师端", "https://reactor-physics-agent.onrender.com/admin"),
        ("课程", "核反应堆物理"),
        ("更新", "2026-11-10"),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in info:
        cells = t.add_row().cells
        r = cells[0].paragraphs[0].add_run(k)
        set_font(r, 10.5, True, GRAY)
        cells[0].width = Cm(3)
        r = cells[1].paragraphs[0].add_run(v)
        set_font(r, 10.5, False, DARK)
    doc.add_page_break()

    # ---------- 目录 / 一分钟了解 ----------
    h1(doc, "这本手册怎么用")
    para(doc, "这是一门核反应堆物理课程的 AI 助教：答案可回翻教材原文，计算由确定性引擎给出，"
              "题卡、错题本、知识图谱、学习计划都会自动联动。教师端可以看全班的掌握度与错题根因。")
    para(doc, "建议阅读顺序：学生先看 1–8 节；教师加看第 10 节；所有人务必看第 11 节「数据备份」。", bold=True)
    table(doc, ["章节", "内容"], [
        ["1", "快速开始：登录与三栏界面"],
        ["2", "提问、证据卡与公式"],
        ["3", "10 个模块速查"],
        ["4", "知识图谱"],
        ["5", "刷题、判分与掌握度"],
        ["6", "学习计划"],
        ["7", "便签、历史、命令面板"],
        ["8", "语音、拍照与常用技巧"],
        ["9", "手机端 / PWA"],
        ["10", "教师端"],
        ["11", "数据备份与恢复"],
        ["12", "快捷键与常见问题"],
    ], widths=[2, 14])

    # ---------- 1 快速开始 ----------
    h1(doc, "1. 快速开始：登录与三栏界面")
    para(doc, "打开在线地址，输入学号/姓名作为账号、任意密码，点「进入工作台」。首次输入会自动建号；"
              "之后用同一账号+密码可找回个人记录。")
    image(doc, "workbench.jpg", "图 1  工作台总览：①顶栏 ②模块导航 ③对话与公式 ④画布（证据卡） ⑤输入框")
    para(doc, "图 1 五个区域的用途：", bold=True)
    bullet(doc, "① 顶栏：连接状态、当前模型、笔记、历史、复习、搜索（命令面板）、主题切换、意见反馈。")
    bullet(doc, "② 左栏：10 个模块导航；下方是知识库统计（394 段 / 15 文档）与门控阈值 τ=0.40。")
    bullet(doc, "③ 对话：消息、思考过程、工具卡、Markdown 与 KaTeX 公式。")
    bullet(doc, "④ 画布：证据卡 / 计算卡 / 曲线 / 对比 / 批注 / 题卡 / 错题本 / 知识图谱。")
    bullet(doc, "⑤ 输入框：Enter 发送、Shift+Enter 换行；左侧可新会话、语音输入、拍题。")

    # ---------- 2 提问 ----------
    h1(doc, "2. 提问、证据卡与公式")
    para(doc, "直接用自然语言提问即可。注意回答上方的「工具卡」显示 Agent 调用了什么工具；右栏每段证据都带"
              "「文档 · 章节 · chunk_id · 相关度」，可展开全文或「围绕此段追问」。")
    table(doc, ["想做什么", "这样问", "会得到"], [
        ["问概念", "什么是缓发中子？为什么它对反应堆控制很重要？", "回答 + 证据卡 + 公式 + 出处"],
        ["算题", "k_eff=1.05 时反应性是多少 pcm？", "计算卡：输入 / 步骤 / 结果"],
        ["刷题", "考我一道题", "题卡：先自己想 → 看解析 → 判分"],
        ["查关系", "点堆动力学依赖哪些前置知识？", "知识图谱 / 前置关系"],
    ], widths=[3, 8, 5])
    para(doc, "如果出现「知识库未收录」，不是系统出错，而是检索覆盖率低于门控阈值 τ=0.40 时的主动拒答。"
              "换课程里的术语再问即可（如有效增殖系数、缓发中子、多普勒展宽、氙中毒）。", color=GRAY)
    para(doc, "公式会自动排版：回答里用 LaTeX（行内 $...$、行间 $$...$$），页面渲染成分式。", size=10)

    # ---------- 3 模块 ----------
    h1(doc, "3. 10 个模块速查")
    table(doc, ["模块", "适合问什么", "主要产出"], [
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
    ], widths=[4, 8, 5])

    # ---------- 4 图谱 ----------
    h1(doc, "4. 知识图谱")
    para(doc, "左栏「知识图谱」打开十章彩色星图：节点颜色=章节，节点大小=关联数，中心点=学习状态"
              "（未学 / 在学 / 已掌握 / 需复习）。")
    image(doc, "graph.jpg", "图 2  知识图谱：按章分簇的星图，可搜索、缩放、点节点看详情")
    bullet(doc, "搜索框可搜知识点或 kp_id；点章名 pill 聚焦该章。")
    bullet(doc, "悬停高亮一跳邻居；点节点看定义、要点、易错、前置/后继。")
    bullet(doc, "层级 L1–L4 与章筛选可隐藏；右上角可切「浅色/星图」主题。")

    # ---------- 5 刷题 ----------
    h1(doc, "5. 刷题、判分与掌握度")
    para(doc, "输入「考我一道题」，或在概念辨析 / 错题模块里出题。题卡先自己想 →「我先想想」看解析 →"
              "「自动判分」或自评「我会了 / 还不会」。")
    image(doc, "quiz.jpg", "图 3  题卡自动判分：分数 / 评语 / 漏掉的点 / 参考答案，并回写掌握度")
    bullet(doc, "自动判分：星火对照参考答案给分，约 10–15 秒；不及格自动进错题本。")
    bullet(doc, "自评：展开解析后点「我会了 / 还不会」，同样回写掌握度。")
    bullet(doc, "掌握度变化会同步到知识图谱节点颜色与学习计划。")

    # ---------- 6 学习计划 ----------
    h1(doc, "6. 学习计划")
    para(doc, "左栏「学习计划」按掌握度、到期复习和前置依赖安排今天学什么。")
    image(doc, "study.jpg", "图 4  学习计划：今日任务、下一步建议、掌握度统计与快捷入口")
    bullet(doc, "今日任务：到期复习（需复习 1 天 / <75% 3 天 / ≥75% 7 天）。")
    bullet(doc, "下一步建议：按图谱前置关系推荐「前置已掌握」的知识点。")
    bullet(doc, "点「去复习 / 去学习」自动切到对应模块并发起提问。")

    # ---------- 7 便签/历史/命令 ----------
    h1(doc, "7. 便签、历史与命令面板")
    para(doc, "顶栏「笔记」打开可拖拽便签：拖动标题栏移动，支持多张、颜色、折叠、Markdown/公式预览，按账号自动保存。")
    image(doc, "sticky.jpg", "图 5  可拖拽便签：随手记录，自动保存", width=14)
    para(doc, "顶栏「历史」按天保存会话，点一条恢复消息 + 最近画布；「复习」打开到期复习抽屉。")
    para(doc, "Ctrl/⌘ + K 打开命令面板，可搜索模块、直接发预设问题、新会话、历史、复习、便签、教师端等。")
    image(doc, "palette.jpg", "图 6  命令面板（Ctrl/⌘ + K）：搜索模块 / 提问 / 操作")

    # ---------- 8 语音拍照 ----------
    h1(doc, "8. 语音、拍照与常用技巧")
    bullet(doc, "语音输入：输入框麦克风（Chrome/Edge，需麦克风权限），识别结果进入草稿。")
    bullet(doc, "朗读：助手消息操作条「朗读 / 停止」。")
    bullet(doc, "拍题：输入框回形针 → 选图/拍照，发送时自动 OCR；印刷体效果最好，手写/复杂公式有限。")
    bullet(doc, "导出：画布右上「导出 Markdown」「打印 / 另存 PDF」。")

    # ---------- 9 手机 ----------
    h1(doc, "9. 手机端 / PWA")
    para(doc, "手机浏览器打开同一网址即可：底部固定「模块 / 对话 / 画布 / 图谱」，左栏变抽屉；"
              "可「添加到主屏幕」全屏打开（无离线缓存，断网不能用）。")
    image(doc, "mobile.jpg", "图 7  手机端：底部导航 + 对话 + 画布", width=7.2)

    # ---------- 10 教师 ----------
    h1(doc, "10. 教师端")
    para(doc, "打开 /admin，可看：语料与图谱规模、账号与消息、拒答率/覆盖率、错题根因、"
              "学习者模型（各状态人数 + 最需要关注的知识点）、语料清单、待复核段落、账号列表。")
    para(doc, "注意：教师端目前没有单独登录鉴权，仅限内部教学使用；公网正式开课建议加访问控制。", color=GRAY)

    # ---------- 11 数据 ----------
    h1(doc, "11. 数据备份与恢复（重要）")
    para(doc, "对话、画布、便签、掌握度镜像会自动保存在当前浏览器；但服务器是 Render 免费档，"
              "重启/重部署会清空服务端数据（账号、历史、掌握度、错题本服务端部分）。", bold=True)
    bullet(doc, "换设备或重启前：顶栏「历史」→ 底部「导出备份」（JSON）。")
    bullet(doc, "新设备/恢复：同一位置「导入备份」，刷新后生效。")
    bullet(doc, "备份只增不减；错题按题面+trace 去重。建议每周导出一次。")

    # ---------- 12 快捷键/FAQ ----------
    h1(doc, "12. 快捷键与常见问题")
    table(doc, ["快捷键", "作用"], [
        ["Enter", "发送"],
        ["Shift + Enter", "换行"],
        ["Ctrl/⌘ + K", "命令面板"],
        ["Ctrl/⌘ + /", "聚焦输入框"],
        ["Esc", "关闭命令面板 / 历史 / 复习 / 便签"],
    ], widths=[5, 11])
    h2(doc, "常见问题")
    para(doc, "Q：回答为什么慢？  A：星火首答约 10–18 秒；相同问题会命中缓存；计算/出题通常毫秒级。", after=2)
    para(doc, "Q：公式不渲染？  A：点「重新回答」；系统已要求模型用 $...$ / $$...$$。", after=2)
    para(doc, "Q：拍题不准？  A：拍正、清晰、光线均匀，或补一句文字描述。", after=2)
    para(doc, "Q：数据丢了？  A：有备份就导入；没备份则免费档重启后无法找回。", after=2)
    para(doc, "Q：能离线用吗？  A：不能，需要联网访问；本地部署可完全离线（见 DEPLOY.md）。", after=2)

    # ---------- 尾页 ----------
    h2(doc, "已知限制（如实说）")
    bullet(doc, "Render 免费档：15 分钟闲置休眠、无持久盘（数据会重置）。")
    bullet(doc, "只有 Spark 文本模型，无多模态视觉；拍题靠 tesseract OCR。")
    bullet(doc, "自动判分约 10–15 秒；复杂主观题建议对照参考答案。")
    bullet(doc, "历史/掌握度/便签跨设备不同步（靠导出/导入）。")

    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
