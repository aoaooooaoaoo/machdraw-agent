"""工具 thread_calc：螺纹比例画法（调用 app.domain.thread 确定性引擎）。"""
from __future__ import annotations

import importlib

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def thread_calc(ctx: ToolContext, spec: str = "", **_) -> ToolOutcome:
    try:
        th = importlib.import_module("app.domain.thread")
    except ImportError:
        return ToolOutcome(ok=False, summary="螺纹引擎尚未就绪", detail="app/domain/thread.py 缺失")
    try:
        d = th.thread_drawing(spec or "")
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="无法解析螺纹标记", detail=str(exc))
    except Exception as exc:
        return ToolOutcome(ok=False, summary=f"螺纹计算失败：{type(exc).__name__}", detail=str(exc))
    return ToolOutcome(
        summary=f"{d.get('spec')} · 大径 {d.get('d')} 小径 {d.get('d1')}",
        detail="\n".join(d.get("points") or []),
        artifact_type="coach",
        artifact_data={"kind": "thread", "data": d},
        payload={"result": d},
    )


TOOL = ToolSpec(
    name="thread_calc",
    label="螺纹比例画法 · {spec}",
    description=(
        "按 GB/T 4459.1-1995 比例画法给出螺纹大径/小径/中径与画法要点，"
        "支持 M10、M10×1.5、M20×2-6H、Tr24×5、G1/2。问螺纹标记或画法时调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "spec": {
                "type": "string",
                "description": "螺纹标记，如 \"M10\"、\"M10×1.5\"、\"M20×2-6H\"、\"Tr24×5\"、\"G1/2\"",
            },
        },
        "required": ["spec"],
    },
    run=thread_calc,
)
