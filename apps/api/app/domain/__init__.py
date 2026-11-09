"""核反应堆物理确定性计算引擎（domain）。

七个纯函数引擎（不依赖 FastAPI / 工具层），每个公开函数返回结构化 dict
（``inputs / results / steps / formulas / refs / notes``）：

* :mod:`critical`   单群/修正单群临界：k∞、M²、B_m²、B_g²、不泄漏概率、临界尺寸
* :mod:`kinetics`   点堆动力学：六组缓发中子、倒时方程、周期、瞬发跳跃、阶跃响应
* :mod:`poison`     碘-氙 / 钷-钐链的平衡与暂态、碘坑指标
* :mod:`burnup`     燃耗深度、²³⁵U 消耗、转换比、线性反应性模型循环长度
* :mod:`reactivity` 反应性换算（k↔ρ、pcm/mk/$）、温度系数、功率亏损
* :mod:`spectrum`   Watt/Maxwell/Fermi/压水堆合成谱、群平均截面、中子温度
* :mod:`rod`        控制棒积分/微分价值、硼价值、临界硼浓度

所有公式、常数均标注教材出处（《核反应堆物理》吴宏春编著/曹良志等参编，
西安交大 2013，章·节·页），锚点测试见 ``apps/api/tests/anchors/``。
"""
from . import burnup, critical, kinetics, poison, reactivity, rod, spectrum

__all__ = [
    "critical",
    "kinetics",
    "poison",
    "burnup",
    "reactivity",
    "spectrum",
    "rod",
]
