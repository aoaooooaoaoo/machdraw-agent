/**
 * SSE 解析器（POST + ReadableStream）。
 *
 * 为什么不用 EventSource：EventSource 只能 GET，而 /api/chat 需要 POST 带 body 与 X-Account。
 *
 * 兼容目标（docs/05 §2.1–2.2 实测协议）：
 *   data: {"type":"thinking","text":"..."}\n\n
 *   ...
 *   data: [DONE]\n\n
 *
 * 容错要求：
 *   1. 帧之间可能夹着**不带 `data:` 前缀**的进度行，如 {"revision":2} —— 跳过，不能崩；
 *   2. 网络分片可能在任意字节处截断（甚至切在 UTF-8 多字节中间）—— 用流式 TextDecoder 缓冲；
 *   3. 单帧 JSON 解析失败（脏帧）—— 跳过该帧并计数，不让整个对话失败；
 *   4. 服务端可能不发结尾空行 —— 流结束时把缓冲区里剩余的 data 行也吃掉；
 *   5. [DONE] 之后立即停止读取并 cancel reader。
 */
import type { ChatRequestBody, SSEEvent } from './types';

export type StreamOutcome = 'done' | 'closed';

export interface StreamStats {
  events: number;
  dropped: number;
  revisionLines: number;
  outcome: StreamOutcome;
}

export interface ChatStreamOptions {
  account: string;
  signal?: AbortSignal;
  onEvent: (ev: SSEEvent) => void;
  /** 调试用：每个被跳过的行都会回传（默认不记录，避免控制台噪音） */
  onSkip?: (line: string, reason: 'no-data-prefix' | 'bad-json' | 'empty') => void;
}

const DATA_PREFIX = 'data:';
const DONE_SENTINEL = '[DONE]';

function trimData(payload: string): string {
  // 允许 "data:{...}" 与 "data: {...}" 两种写法
  return payload.startsWith(' ') ? payload.slice(1) : payload;
}

/** 解析一个 SSE 事件块（以空行分隔的多行），返回其中的 data 载荷（可能为 null）。 */
function extractData(block: string, onSkip?: ChatStreamOptions['onSkip']): string | null {
  const dataLines: string[] = [];
  for (const rawLine of block.split('\n')) {
    const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;
    if (!line.startsWith(DATA_PREFIX)) {
      if (line.trim() !== '') onSkip?.(line, 'no-data-prefix');
      continue;
    }
    dataLines.push(trimData(line.slice(DATA_PREFIX.length)));
  }
  if (dataLines.length === 0) return null;
  // 规范里多行 data 用换行拼接；本项目服务端每帧只有一行，这里仍然兼容。
  return dataLines.join('\n');
}

export class ChatHTTPError extends Error {
  readonly status: number;
  readonly body: string;
  constructor(status: number, message: string, body: string) {
    super(message);
    this.name = 'ChatHTTPError';
    this.status = status;
    this.body = body;
  }
}

/** 从 FastAPI / 通用错误体里取可读信息：detail > message > error > 原文。 */
export function extractErrorMessage(raw: string, fallback: string): string {
  const text = (raw || '').trim();
  if (!text) return fallback;
  try {
    const body = JSON.parse(text);
    if (typeof body === 'string') return body;
    if (body && typeof body === 'object') {
      const candidate = body.detail ?? body.message ?? body.error ?? body.msg;
      if (typeof candidate === 'string' && candidate.trim()) return candidate;
      // FastAPI 422 的 detail 是数组
      if (Array.isArray(candidate) && candidate.length > 0) {
        const first = candidate[0];
        if (first && typeof first === 'object' && typeof first.msg === 'string') return first.msg;
      }
      if (typeof body.code === 'string' && body.code) return `${body.code}: ${text}`;
    }
  } catch {
    /* 不是 JSON，直接返回原文 */
  }
  return text.length > 500 ? `${text.slice(0, 500)}…` : text;
}

/**
 * 打开 /api/chat 的 SSE 流并逐帧回调。
 * 正常结束返回 'done'（收到 [DONE]），流被关闭返回 'closed'。
 */
export async function streamChat(
  body: ChatRequestBody,
  opts: ChatStreamOptions,
): Promise<StreamStats> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      'X-Account': opts.account,
    },
    body: JSON.stringify(body),
    signal: opts.signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new ChatHTTPError(
      res.status,
      extractErrorMessage(text, `对话请求失败（HTTP ${res.status}）`),
      text,
    );
  }
  if (!res.body) {
    throw new ChatHTTPError(res.status, '响应没有可读流（浏览器不支持 ReadableStream？）', '');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  const stats: StreamStats = { events: 0, dropped: 0, revisionLines: 0, outcome: 'closed' };
  let buffer = '';

  const handleBlock = (block: string): boolean => {
    const data = extractData(block, opts.onSkip);
    if (data === null) return false;
    const payload = data.trim();
    if (!payload) {
      opts.onSkip?.('', 'empty');
      return false;
    }
    if (payload === DONE_SENTINEL) return true;

    let ev: SSEEvent;
    try {
      ev = JSON.parse(payload) as SSEEvent;
    } catch {
      stats.dropped += 1;
      opts.onSkip?.(payload, 'bad-json');
      return false;
    }
    if (!ev || typeof ev !== 'object' || typeof ev.type !== 'string') {
      stats.dropped += 1;
      opts.onSkip?.(payload, 'bad-json');
      return false;
    }
    stats.events += 1;
    opts.onEvent(ev);
    return false;
  };

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE 事件以空行分隔；统一 CRLF 后再按 "\n\n" 切。
      buffer = buffer.replace(/\r\n/g, '\n');
      let sep = buffer.indexOf('\n\n');
      while (sep !== -1) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        if (handleBlock(block)) {
          stats.outcome = 'done';
          await reader.cancel().catch(() => undefined);
          return stats;
        }
        sep = buffer.indexOf('\n\n');
      }
    }

    // 流结束：冲掉解码器与最后一个不完整帧（服务端最后一个 [DONE] 有时没有尾随空行）
    buffer += decoder.decode();
    buffer = buffer.replace(/\r\n/g, '\n');
    if (buffer.trim()) {
      const rest = buffer;
      buffer = '';
      if (handleBlock(rest)) stats.outcome = 'done';
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      /* 已 cancel / 已释放 */
    }
  }

  return stats;
}

/**
 * 纯函数版本：给一段完整 SSE 文本，返回事件数组。
 * 只用于单测/离线回放（真实链路走 streamChat）。
 */
export function parseSSEText(text: string): { events: SSEEvent[]; dropped: number } {
  const events: SSEEvent[] = [];
  let dropped = 0;
  const normalized = text.replace(/\r\n/g, '\n');
  for (const block of normalized.split('\n\n')) {
    const data = extractData(block);
    if (!data) continue;
    const payload = data.trim();
    if (!payload || payload === DONE_SENTINEL) continue;
    try {
      const ev = JSON.parse(payload) as SSEEvent;
      if (ev && typeof ev.type === 'string') events.push(ev);
      else dropped += 1;
    } catch {
      dropped += 1;
    }
  }
  return { events, dropped };
}
