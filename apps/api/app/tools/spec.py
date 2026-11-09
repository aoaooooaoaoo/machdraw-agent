"""工具规格（ToolSpec）：一个工具对外暴露的全部元数据。

约定（自注册的唯一契约）::

    # app/tools/<name>.py
    from .base import ToolContext, ToolOutcome
    from .spec import ToolSpec

    def <name>(ctx: ToolContext, ...) -> ToolOutcome: ...

    TOOL = ToolSpec(
        name="<name>",              # 必须等于文件名（去掉 .py），注册时硬校验
        label="展示文案 · {参数名}",  # 可含 {参数名} 占位符，供前端/事件流展示
        description="给模型/编排器看的说明",
        parameters={...},           # JSON Schema（object），禁止为空
        run=<name>,
    )

新增工具：新建 ``app/tools/<name>.py`` 并导出 ``TOOL`` 即可，无需修改任何公共文件。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:  # 仅类型检查期导入，避免运行期循环 import
    from .base import ToolOutcome

__all__ = ["ToolSpec"]


@dataclass(frozen=True)
class ToolSpec:
    """一个工具的规格。

    Attributes:
        name: 工具名，必须等于所在模块的文件名（去掉 ``.py``）。
        label: 展示文案，可含 ``{参数名}`` 占位符（如 ``"检索课程原文 · {query}"``）。
        description: 给模型/编排器看的说明，决定"什么时候该调用它"。
        parameters: 参数的 JSON Schema（``type: object``），不能为空。
        run: 实际执行函数，签名 ``(ctx, **args) -> ToolOutcome``。
    """

    name: str
    label: str
    description: str
    parameters: dict[str, Any]
    run: Callable[..., "ToolOutcome"]
