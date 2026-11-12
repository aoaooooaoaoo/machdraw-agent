"""用同一份内容生成发布版网页和 Word 说明书。"""
from __future__ import annotations

from html import escape
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "guide"
BASE = "https://reactor-physics-agent.onrender.com"
TITLE = "核反应堆物理 AI 助教使用说明"
VERSION = "学生与教师手册 v2.0  ·  2026 年 11 月"
FONT = "微软雅黑"

SECTIONS = [
    ("start", "快速开始", [
        ("p", "本手册适用于《核反应堆物理》本科课程。学生可查教材依据、沿图谱复习，并完成需要计算、取证和修订结论的工程案例。教师可按同一道题批阅作业，复核候选错因并导出统计。"),
        ("links", [("学生工作台", f"{BASE}/"), ("课程图谱与案例", f"{BASE}/?view=course&tab=cases"),
                   ("教师主观题批阅", f"{BASE}/admin/homework")]),
        ("h", "学生首次使用"),
        ("steps", [
            "打开学生工作台，按课程约定输入账号和密码。以后用同一账号和密码登录。",
            "在输入框提问，或从左栏选择教材与概念溯源、课程图谱与案例、学习计划等模块。",
            "阅读回答后，打开右侧证据卡核对教材章节。遇到算题，可查看计算卡的输入、过程与结果。"
        ]),
        ("h", "按任务找入口"),
        ("table", [("要做什么", "从哪里进入"),
                   ("查定义、公式或教材出处", "教材与概念溯源 → 查看证据卡"),
                   ("梳理先学什么", "课程图谱与案例 → 知识图谱或问题图谱"),
                   ("练习工程判断", "课程图谱与案例 → 工程案例"),
                   ("查看分项作答记录", "课程图谱与案例 → 能力图谱"),
                   ("批改同一道主观题", "教师端 → 主观题批阅")]),
    ]),
    ("graphs", "三张图谱", [
        ("p", "左栏打开「课程图谱与案例」，用页面上方的标签切换。三张图谱分别回答概念怎样相连、问题怎样递进、能力怎样通过作答体现。"),
        ("table", [("图谱", "用途与操作"),
                   ("知识图谱", "179 个知识点、289 条关系。可按章或层级浏览，搜索术语或编号。点节点可看定义、前置、易错点、课程出处和关联案例。"),
                   ("问题图谱", "37 道问题、37 条递进关系。可按关键词或编号搜索，也可按案例查看前置题链。点问题看关联知识点、提示和递进理由。"),
                   ("能力图谱", "8 项能力。点能力看前置与后续能力，以及对应案例、综合问题和评分项。展开已有练习可查看作答证据。")]),
        ("h", "沿着一个问题复习"),
        ("steps", [
            "在问题图谱搜索 Q-037，查看两份计算报告为何需要分别核对统计精度和归一口径。",
            "点「独立估计差值的合成标准误」查看概念，再从知识点详情进入「两份计算结果的一致性复核」。",
            "完成案例并保存自评后，打开「不确定性评估」，查看对应评分项及初判、所选材料和修订作答。"
        ]),
        ("p", "能力记录区分自评与模型建议。每个案例在当前浏览器按账号保留最近五条记录。"),
    ]),
    ("cases", "工程案例", [
        ("p", "在工程案例页按主题筛选或用关键词搜索。七个案例的数值为合成教学数据，概念出处可从案例或知识图谱回查。"),
        ("table", [("案例", "练习重点"),
                   ("堆芯功率分布报告复核", "功率归一、峰均比和空间分辨率"),
                   ("两群模型结果差异追查", "按通量权重折叠响应，用对照复算追查差异"),
                   ("卸料燃耗统计口径审查", "区分整体加权均值、最高批均值和组件最大值"),
                   ("探测器计数记录复核", "统一计数口径，扣除背景并说明比较条件"),
                   ("停堆后两条信号的解释", "区分衰变释热、归一基准和仪器显示下限"),
                   ("温度反馈时序复盘", "核对时序与反馈分项，说明证据支持的归因"),
                   ("两份计算结果的一致性复核", "比较差值与标准误，分别核对统计误差和模型口径")]),
        ("h", "完成一次推演"),
        ("steps", [
            "阅读题设和表格，写下初步判断、计算依据和还缺的资料。",
            "点「记录初判，选择补充证据」，选一份材料。先看这份材料实际提供了什么。",
            "修订结论并提交。按对应量规自评或获取模型评阅建议，可展开对照另一条证据路径。"
        ]),
    ]),
    ("teacher", "主观题批阅", [
        ("p", "在教师端顶部点「主观题批阅」。可用内置案例，也可填写自定义题目、评分项、分值、得分要点和预设错因。"),
        ("steps", [
            "选定题目，再导入同一道题的匿名作答。可逐份录入、粘贴两列表格或导入 CSV。",
            "用「按错答示例扫描」匹配量规里的错答短句，或用「批量模型预评」查看逐项建议。展开候选错因组，核对引文及原答卷。",
            "可改错因名称、勾选适用作答，并把错因加入待批阅记录。检查每项分数、补充错因或评语后，点「确认并继续批阅」。",
            "展开本题错因统计查看相关答卷，或导出本题错因报告。分母为教师确认的答卷数，同一答卷中的同一错因只计一次。"
        ]),
        ("h", "导入与演示"),
        ("p", "CSV 可使用「匿名编号,作答」或「id,answer」作表头。含换行或逗号的答案用双引号包住，答案里的双引号写成两个。每道题内匿名编号唯一。"),
        ("p", "内置案例提供「填入演示作答」，可先检查填入内容，再点「批量导入」。演示作答用于体验功能，班级统计应基于本班真实匿名作答。"),
        ("h", "模型建议与数据"),
        ("p", "主动点击模型预评时，题目、量规和对应匿名作答会发送给配置的模型。示例扫描和人工阅卷可独立使用。模型评分和归组均由教师复核。"),
    ]),
    ("records", "记录备份与常见问题", [
        ("table", [("记录", "如何保存"),
                   ("对话、错题及掌握度", "在顶栏「历史」中导出学习备份。需要恢复时从同一入口导入。"),
                   ("教师批阅、量规及错因", "记录保存在当前浏览器。从主观题批阅页导出批阅 JSON，再在目标浏览器用「恢复备份」合并。"),
                   ("案例初判、修订与自评", "可在能力图谱回看。记录按账号保存在当前浏览器，换浏览器后需重新练习。")]),
        ("h", "常见操作"),
        ("p", "网页加载慢时，稍等服务唤醒。重新打开后可用顶栏连接状态确认后端是否连通。"),
        ("p", "问题图谱信息太多时，选「按案例看前置」聚焦一条题链。案例页也可先按主题过滤。"),
        ("p", "模型暂不可用时，案例可按量规自评，教师可做示例扫描与人工批阅。示例扫描的覆盖范围取决于量规中列出的短句。"),
        ("p", "拍照识别适合清晰的印刷体。公式、上下标或手写内容识别有误时，可在输入框补写关键文字。"),
        ("p", "云端服务使用临时磁盘时，重启或重新部署可能影响服务器记录。重要作业和学习数据应先从对应页面导出。"),
        ("links", [("在线手册", f"{BASE}/guide/"), ("PDF 版", f"{BASE}/guide/manual-v2.pdf"),
                   ("Word 版", f"{BASE}/guide/manual-v2.docx")]),
    ]),
]


def element(tag, **attributes):
    item = OxmlElement(f"w:{tag}")
    for name, value in attributes.items():
        item.set(qn(f"w:{name}"), str(value))
    return item


def hyperlink(paragraph, label, url):
    rel = paragraph.part.relate_to(
        url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    link = element("hyperlink")
    link.set(qn("r:id"), rel)
    run = element("r")
    style = element("rPr")
    style.append(element("color", val="1D4E8F"))
    style.append(element("u", val="single"))
    run.append(style)
    text = element("t")
    text.text = label
    run.append(text)
    link.append(run)
    paragraph._p.append(link)


def word_table(doc, rows):
    table = doc.add_table(rows=0, cols=2)
    table.autofit = False
    for column, width in zip(table.columns, (5.1, 11.9)):
        column.width = Cm(width)
    borders = element("tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(element(edge, val="single", sz=5, color="D9D9D9"))
    table._tbl.tblPr.append(borders)
    padding = element("tblCellMar")
    for side in ("top", "bottom", "left", "right"):
        padding.append(element(side, w=90, type="dxa"))
    table._tbl.tblPr.append(padding)
    for index, row in enumerate(rows):
        record = table.add_row()
        record._tr.get_or_add_trPr().append(element("cantSplit"))
        if index == 0:
            record._tr.get_or_add_trPr().append(element("tblHeader"))
        for cell, value in zip(record.cells, row):
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(value)
            run.bold = index == 0
            run.font.size = Pt(10.5)
            if index == 0:
                cell._tc.get_or_add_tcPr().append(element("shd", fill="E8EFF8"))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def write_docx():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(2)
    for name in ("Normal", "Title", "Subtitle", "Heading 1", "Heading 2", "List Number"):
        style = doc.styles[name]
        style.font.name = FONT
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT)
        style.paragraph_format.line_spacing = 1.24
        style.paragraph_format.space_after = Pt(7)
    doc.styles["Normal"].font.size = Pt(11)
    doc.styles["Title"].font.size = Pt(24)
    doc.styles["Heading 1"].font.size = Pt(20)
    doc.styles["Heading 2"].font.size = Pt(13)
    title_props = doc.styles["Title"].element.get_or_add_pPr()
    for border in title_props.findall(qn("w:pBdr")):
        title_props.remove(border)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run("核反应堆物理 AI 助教  ·  ").font.size = Pt(9)
    footer._p.append(element("fldSimple", instr="PAGE"))
    doc.add_paragraph(TITLE, style="Title")
    doc.add_paragraph(VERSION, style="Subtitle")
    for index, (_, name, blocks) in enumerate(SECTIONS):
        heading = doc.add_heading(name, level=1)
        heading.paragraph_format.page_break_before = bool(index)
        for kind, content in blocks:
            if kind == "p":
                doc.add_paragraph(content)
            elif kind == "h":
                doc.add_heading(content, level=2)
            elif kind == "steps":
                for number, step in enumerate(content, start=1):
                    paragraph = doc.add_paragraph(f"{number}. {step}")
                    paragraph.paragraph_format.left_indent = Cm(.45)
                    paragraph.paragraph_format.first_line_indent = Cm(-.45)
            elif kind == "table":
                word_table(doc, content)
            elif kind == "links":
                paragraph = doc.add_paragraph()
                for position, (label, url) in enumerate(content):
                    if position:
                        paragraph.add_run("  ·  ")
                    hyperlink(paragraph, label, url)
    doc.core_properties.title = TITLE
    doc.core_properties.subject = VERSION
    doc.save(OUT / "manual-v2.docx")


CSS = """
*{box-sizing:border-box}body{margin:0;font:16px/1.7 system-ui,'Microsoft YaHei',sans-serif;color:#182437;background:#f1f5fa}
header,main{max-width:880px;margin:auto;padding:1.5rem 1rem}header{padding-bottom:0}
h1,h2,h3{line-height:1.32;margin:.3rem 0 .9rem}h1{font-size:clamp(1.55rem,4vw,2.25rem)}
h2{font-size:1.4rem}h3{font-size:1.05rem;margin-top:1.25rem}p{margin:.55rem 0 .9rem}
section{background:#fff;border:1px solid #d7e1ed;border-radius:12px;padding:clamp(1rem,3vw,1.65rem);margin:0 0 1rem}
nav,.links{display:flex;flex-wrap:wrap;gap:.35rem 1rem}nav{margin-top:1rem}a{color:#174b92;text-underline-offset:.18em}
table{width:100%;border-collapse:collapse;margin:.8rem 0}th,td{border:1px solid #d9d9d9;padding:.48rem .65rem;text-align:left}
th{background:#e8eff8}td:first-child{width:30%}ol{padding-left:1.45rem}li{margin:.35rem 0}
@media print{body{background:white}nav{display:none}header,main{padding:0}section{border:0;border-radius:0;break-after:page}}
"""


def write_html():
    def links(items):
        return "".join(f'<a href="{escape(url, quote=True)}">{escape(label)}</a>' for label, url in items)

    parts = [
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{TITLE}</title><style>{CSS}</style>",
        f"<header><h1>{TITLE}</h1><p>{VERSION}</p>",
        '<div class="links"><a href="./manual-v2.pdf">下载 PDF</a><a href="./manual-v2.docx">下载 Word</a></div>',
        f'<nav aria-label="手册目录">{links([(name, f"#{key}") for key, name, _ in SECTIONS])}</nav></header><main>',
    ]
    for key, name, blocks in SECTIONS:
        parts.append(f'<section id="{key}"><h2>{name}</h2>')
        for kind, content in blocks:
            if kind in ("p", "h"):
                tag = "p" if kind == "p" else "h3"
                parts.append(f"<{tag}>{escape(content)}</{tag}>")
            elif kind == "links":
                parts.append(f'<p class="links">{links(content)}</p>')
            elif kind == "steps":
                parts.append("<ol>" + "".join(f"<li>{escape(step)}</li>" for step in content) + "</ol>")
            elif kind == "table":
                heads, *rows = content
                parts.append("<table><thead><tr>" + "".join(f'<th scope="col">{escape(cell)}</th>' for cell in heads)
                             + "</tr></thead><tbody>" + "".join(
                                 "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
                                 for row in rows) + "</tbody></table>")
        parts.append("</section>")
    parts.append("</main></html>")
    (OUT / "index.html").write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    write_docx()
    write_html()
