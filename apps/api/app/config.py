"""全局配置。所有可调参数集中在此，便于用探针集重标定。

课程：核反应堆物理（复刻自机械制图 AI 助教工程，环境变量前缀 RP_）。
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KB_DIR = ROOT / "kb"
DATA_DIR = ROOT / "data"
INDEX_DIR = DATA_DIR / "index"
EVAL_DIR = ROOT / "eval"

# ---- 从 .env 读本地配置（.env 已在 .gitignore，不进仓库）
# 只用来放 API Key 这类**不该进版本库**的东西；检索参数仍走环境变量，方便探针重标定。
# 优先级：真实环境变量 > .env（load_dotenv 默认不覆盖已存在的变量）。
try:
    from dotenv import load_dotenv

    for _cand in (ROOT / ".env", ROOT / "apps" / "api" / ".env"):
        if _cand.exists():
            load_dotenv(_cand, override=False)
except ImportError:
    pass    # 没装 python-dotenv 也不影响，走纯环境变量

# ---- 检索参数（2026-11-09 用 eval/ 的 54 题探针集重标定；旧工程值 λ=0.45/τ=0.55 已不适用）
SPARSE_WEIGHT = float(os.getenv("RP_SPARSE_WEIGHT", "0.45"))   # λ：BM25 通道权重
GATE_TAU = float(os.getenv("RP_GATE_TAU", "0.40"))             # IDF 覆盖率门控阈值（标定集：课内min 0.471 / 课外max 0.326）
OOV_WEIGHT = float(os.getenv("RP_OOV_WEIGHT", "1.2"))          # 语料外实义词的权重倍数
COVERAGE_MODE = os.getenv("RP_COVERAGE_MODE", "docs")          # docs=按召回块判定 / corpus=按全库词表判定
GATE_TAU_CHUNK = float(os.getenv("RP_GATE_TAU_CHUNK", "0.25")) # 单块覆盖率门限（标定集：课内min 0.284 / 课外max 0.223）
GATE_RARE_K = int(os.getenv("RP_GATE_RARE_K", "2"))            # 保留配置项（当前实现未使用稀有词判定）
RECALL_K = int(os.getenv("RP_RECALL_K", "24"))                 # 单通道召回数
TOP_K = int(os.getenv("RP_TOP_K", "6"))                        # 送 LLM 的证据数
MAX_EVIDENCE_CHARS = 1400

# ---- 向量参数
HASH_DIM = 4096                 # hashing tf-idf 维度（语料 <3000 块时足够）
MAX_CHUNK_CHARS = 350           # 子块目标字数
MIN_CHUNK_CHARS = 60

# ---- LLM
LLM_PROVIDER = os.getenv("RP_LLM_PROVIDER", "mock")   # mock | deepseek | openai-compatible
LLM_MODEL = os.getenv("RP_LLM_MODEL", "deepseek-chat")
LLM_BASE_URL = os.getenv("RP_LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("RP_LLM_API_KEY", "") or os.getenv("DEEPSEEK_API_KEY", "")
# 额外请求体参数（JSON 字符串）。主要用于关闭推理模型的思维链：
#   例：RP_LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}
LLM_EXTRA_BODY = os.getenv("RP_LLM_EXTRA_BODY", "")
# 容错：配了 provider 但没给 Key 时自动回落到 mock，避免线上 500/空回答
if LLM_PROVIDER != "mock" and not LLM_API_KEY:
    LLM_PROVIDER = "mock"

# ---- 其它
DB_PATH = DATA_DIR / "app.db"
INTERNAL_ONLY = os.getenv("RP_INTERNAL_ONLY", "1") == "1"   # 是否允许版权受限内容入库
