"""教学模型库：用极简 CSG 描述的典型形体（三视图真投影的输入）。

每个模型都是 `Solid`（若干长方体/棱柱求并，再挖去若干孔），
尺寸取整方便讲解；坐标原点大致取在形体左下前角附近。
"""
from __future__ import annotations

from .solid import Solid, box, prism


def m_box() -> Solid:
    """长方体 100×60×40。"""
    return Solid([box(0, 0, 0, 100, 60, 40)])


def m_l_block() -> Solid:
    """L 形块：底板 100×60×20 + 竖板 30×60×40（贴在左后侧）。"""
    return Solid([
        box(0, 0, 0, 100, 60, 20),
        box(0, 0, 20, 30, 60, 60),
    ])


def m_step() -> Solid:
    """台阶块：两级台阶。"""
    return Solid([
        box(0, 0, 0, 100, 60, 20),
        box(0, 0, 20, 60, 60, 45),
    ])


def m_hole_block() -> Solid:
    """带通孔的方块：120×80×40，中央 Φ24 竖直通孔。"""
    return Solid(
        [box(0, 0, 0, 120, 80, 40)],
        [prism("z", 60, 40, 0, 12, -1, 41)],
    )


def m_tube() -> Solid:
    """圆筒：外 Φ64、内 Φ40、高 70。"""
    return Solid(
        [prism("z", 0, 0, 0, 32, 0, 70)],
        [prism("z", 0, 0, 0, 20, -1, 71)],
    )


def m_shaft() -> Solid:
    """阶梯轴：沿 X 轴，Φ36×L60 + Φ24×L50。"""
    return Solid([
        prism("x", 0, 0, 0, 18, 0, 60),
        prism("x", 0, 0, 0, 12, 60, 110),
    ])


def m_bracket() -> Solid:
    """支架：底板 120×80×16 + 竖板 120×16×60（后侧）+ 两个 Φ16 安装孔。"""
    return Solid(
        [
            box(0, 0, 0, 120, 80, 16),
            box(0, 64, 16, 120, 80, 76),
        ],
        [
            prism("z", 20, 40, 0, 8, -1, 17),
            prism("z", 100, 40, 0, 8, -1, 17),
        ],
    )


def m_cap() -> Solid:
    """端盖：圆盘 Φ80×12 + 凸台 Φ44×20 + 中央 Φ20 通孔。"""
    return Solid(
        [
            prism("z", 0, 0, 0, 40, 0, 12),
            prism("z", 0, 0, 0, 22, 12, 32),
        ],
        [prism("z", 0, 0, 0, 10, -1, 33)],
    )


MODELS: dict[str, dict] = {
    "M-BOX":        {"name": "长方体", "build": m_box},
    "M-L-BLOCK":    {"name": "L 形块", "build": m_l_block},
    "M-STEP":       {"name": "台阶块", "build": m_step},
    "M-HOLE-BLOCK": {"name": "带通孔的方块", "build": m_hole_block},
    "M-TUBE":       {"name": "圆筒", "build": m_tube},
    "M-SHAFT":      {"name": "阶梯轴", "build": m_shaft},
    "M-BRACKET":    {"name": "支架", "build": m_bracket},
    "M-CAP":        {"name": "端盖", "build": m_cap},
}


def build_model(model_id: str) -> Solid:
    if model_id not in MODELS:
        raise ValueError(f"未知模型 {model_id}；可用：{'、'.join(MODELS)}")
    return MODELS[model_id]["build"]()


def model_name(model_id: str) -> str:
    return MODELS.get(model_id, {}).get("name", model_id)
