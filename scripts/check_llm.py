#!/usr/bin/env python
"""LLM 供应商连通性自检。

用途：换模型、换 key、部署到新平台后，用它确认「配置读对了、接口通、返回结构能解析」。

用法：
    python scripts/check_llm.py                 # 读当前环境变量/配置，做一次真实调用
    python scripts/check_llm.py --list          # 只打印当前配置，不发起请求
    MW_LLM_PROVIDER=spark MW_LLM_API_KEY=xxx python scripts/check_llm.py

支持的供应商（都是 OpenAI 兼容协议，本项目 llm.py 直接可用）：
    mock         本地抽取模式，不需要 key
    deepseek     https://api.deepseek.com/v1
    spark        讯飞星火 https://spark-api-open.xf-yun.com/v1   （Lite 免费）
    openai-compatible  任意自建/第三方 OpenAI 兼容端点（含 Ollama）
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PRESETS = {
    # 讯飞星辰 MaaS（ak- 开头的 key；端点带 /v2，模型名 spark-x2.6）
    "maas": {"base": "https://maas-api.cn-huabei-1.xf-yun.com/v2", "model": "spark-x2.6"},
    # 讯飞星火老 HTTP 接口（APIPassword；Lite 免费）
    "spark": {"base": "https://spark-api-open.xf-yun.com/v1", "model": "lite"},
    "deepseek": {"base": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "ollama": {"base": "http://127.0.0.1:11434/v1", "model": "qwen2.5:3b"},
}


def main() -> int:
    from app.config import (
        LLM_API_KEY,
        LLM_BASE_URL,
        LLM_EXTRA_BODY,
        LLM_MODEL,
        LLM_PROVIDER,
    )

    masked = (LLM_API_KEY[:6] + "…" + LLM_API_KEY[-4:]) if len(LLM_API_KEY) > 12 else ("(空)" if not LLM_API_KEY else "***")
    print("=" * 62)
    print("当前 LLM 配置")
    print("=" * 62)
    print(f"  provider = {LLM_PROVIDER}")
    print(f"  model    = {LLM_MODEL}")
    print(f"  base_url = {LLM_BASE_URL}")
    print(f"  api_key  = {masked}")

    if LLM_PROVIDER == "mock":
        print("\n[提示] provider=mock：走本地证据抽取，不调用任何模型。")
        print("       想接真模型，设 MW_LLM_PROVIDER + MW_LLM_API_KEY 后重跑本脚本。")
        print("       预设可用：" + " / ".join(PRESETS))
        return 0

    if not LLM_API_KEY:
        print("\n[FAIL] provider 不是 mock，但 MW_LLM_API_KEY 为空 —— 代码会强制回落 mock。")
        return 1

    if "--list" in sys.argv:
        return 0

    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": "用一句话说明什么是基孔制"}],
        "temperature": 0.2,
        "stream": False,
    }
    if LLM_EXTRA_BODY.strip():
        try:
            extra = json.loads(LLM_EXTRA_BODY)
            if isinstance(extra, dict):
                payload.update(extra)
                print(f"  额外参数 = {json.dumps(extra, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print(f"  [warn] MW_LLM_EXTRA_BODY 不是合法 JSON，已忽略：{LLM_EXTRA_BODY[:60]}")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    print(f"\nPOST {url}")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {LLM_API_KEY}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        print(f"[FAIL] HTTP {e.code}")
        print("  " + detail[:400])
        hint = ""
        if "11200" in detail:
            hint = ("授权错误：账号没有该模型的有效订单/额度。"
                    "\n          · 星火老接口：去 console.xfyun.cn 领取该版本免费额度"
                    "\n          · 星辰 MaaS：去 maas.xfyun.cn 的「API调用」页开通套餐/领取额度")
        elif "11201" in detail:
            hint = "日流控超限 → 明天再用，或换付费/其他供应商"
        elif "11202" in detail or "11203" in detail:
            hint = "并发/秒级流控 → 降低并发"
        elif "10013" in detail or "10014" in detail:
            hint = "内容审核不通过 → 换个问法"
        if hint:
            print("  [诊断] " + hint)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {type(e).__name__}: {e}")
        return 1

    try:
        j = json.loads(raw)
    except json.JSONDecodeError:
        print("[FAIL] 返回不是 JSON：")
        print("  " + raw[:300])
        return 1

    # 星火成功时带 code/message，OpenAI 系没有
    code = j.get("code")
    if code not in (None, 0):
        print(f"[FAIL] code={code} message={j.get('message')}")
        return 1
    try:
        content = j["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("[FAIL] 返回结构里没有 choices[0].message.content：")
        print("  " + raw[:300])
        return 1

    print("[OK] 调用成功")
    print("  回答：" + content[:160].replace("\n", " "))
    if j.get("usage"):
        print("  用量：" + json.dumps(j["usage"], ensure_ascii=False))
    print("\n可以把这个 provider 配到服务上了（本地环境变量 / Render 控制台）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
