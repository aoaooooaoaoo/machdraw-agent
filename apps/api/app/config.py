"""全局配置。所有可调参数集中在此，便于用探针集重标定。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]      # D:\桌面\机械制图agent
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

# ---- 检索参数（起步值，需用 eval/ 的探针集重标定；参考作品 λ=0.35、τ=0.50）
SPARSE_WEIGHT = float(os.getenv("MW_SPARSE_WEIGHT", "0.45"))   # λ：BM25 通道权重
GATE_TAU = float(os.getenv("MW_GATE_TAU", "0.55"))             # IDF 覆盖率门控阈值（32 题探针标定：τ=0.45 时 acc 0.969，课内召回 20/20、课外拒答 11/12）
OOV_WEIGHT = float(os.getenv("MW_OOV_WEIGHT", "1.2"))          # 语料外实义词的权重倍数
COVERAGE_MODE = os.getenv("MW_COVERAGE_MODE", "docs")          # docs=按召回块判定 / corpus=按全库词表判定
GATE_TAU_CHUNK = float(os.getenv("MW_GATE_TAU_CHUNK", "0.45")) # 单块覆盖率门限：没有任何一块能吃下这个问题就拒答
GATE_RARE_K = int(os.getenv("MW_GATE_RARE_K", "2"))            # 保留配置项（当前实现未使用稀有词判定）
RECALL_K = int(os.getenv("MW_RECALL_K", "24"))                 # 单通道召回数
TOP_K = int(os.getenv("MW_TOP_K", "6"))                        # 送 LLM 的证据数
MAX_EVIDENCE_CHARS = 1400

# ---- 向量参数
HASH_DIM = 4096                 # hashing tf-idf 维度（语料 <2000 块时足够）
MAX_CHUNK_CHARS = 350           # 子块目标字数
MIN_CHUNK_CHARS = 60

# ---- LLM
LLM_PROVIDER = os.getenv("MW_LLM_PROVIDER", "mock")   # mock | deepseek | openai-compatible
LLM_MODEL = os.getenv("MW_LLM_MODEL", "deepseek-chat")
LLM_BASE_URL = os.getenv("MW_LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("MW_LLM_API_KEY", "") or os.getenv("DEEPSEEK_API_KEY", "")
# 额外请求体参数（JSON 字符串）。主要用于关闭推理模型的思维链：
#   讯飞 spark-x2.6-4b 实测：默认 115s / 3405 推理 token；带 thinking disabled 后 5.7s / 0 推理 token，回答还更长。
#   例：MW_LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}
LLM_EXTRA_BODY = os.getenv("MW_LLM_EXTRA_BODY", "")

# ---- 其它
DB_PATH = DATA_DIR / "app.db"
INTERNAL_ONLY = os.getenv("MW_INTERNAL_ONLY", "1") == "1"   # 是否允许版权受限内容入库
