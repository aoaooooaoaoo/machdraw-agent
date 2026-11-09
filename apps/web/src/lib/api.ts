/**
 * 后端只读接口 + 账号接口。
 * 开发期由 vite.config.ts 的 /api 代理转发到 http://127.0.0.1:8077；
 * 生产期同源部署，因此这里一律用相对路径，不把后端地址写死进前端。
 */
import { extractErrorMessage } from './sse';
import type {
  GraphFull,
  GraphNodeDetail,
  HealthInfo,
  ModuleManifest,
} from './types';

export class ApiError extends Error {
  readonly status: number;
  readonly body: string;
  constructor(status: number, message: string, body = '') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.headers || {}),
      },
    });
  } catch (err) {
    throw new ApiError(0, `无法连接后端：${(err as Error).message}`, '');
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new ApiError(res.status, extractErrorMessage(text, `HTTP ${res.status}`), text);
  }
  // res.json() 内部按 UTF-8 解码，中文不会乱码（后端已带 charset=utf-8）
  return (await res.json()) as T;
}

export interface HealthResponse extends HealthInfo {}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health');
}

export async function getModules(): Promise<ModuleManifest[]> {
  const data = await request<{ modules: ModuleManifest[] }>('/api/modules');
  return Array.isArray(data.modules) ? data.modules : [];
}

export interface LoginResult {
  ok: boolean;
  account: string;
  created: boolean;
  records?: Record<string, unknown>;
}

export async function login(account: string, password: string): Promise<LoginResult> {
  return request<LoginResult>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ account, password }),
  });
}

/* ---------------------------------------------------------------- 知识图谱 */

/**
 * /api/graph 一次 40–50 KB，模块级缓存：只在第一次需要时拉一次，
 * 用于取「N 节点 · M 关系 · K 课程问题」的全局计数与课程问题，
 * 画布本身的数据仍来自 chat 的 graph artifact。
 */
let graphPromise: Promise<GraphFull> | null = null;

export function getGraph(): Promise<GraphFull> {
  if (!graphPromise) {
    graphPromise = request<GraphFull>('/api/graph').catch((err) => {
      graphPromise = null; // 失败不缓存，便于重试
      throw err;
    });
  }
  return graphPromise;
}

/** 点画布节点时换焦点：单元详情（node + neighbors + prereq 链）。 */
export async function getGraphNode(nodeId: string): Promise<GraphNodeDetail> {
  return request<GraphNodeDetail>(`/api/graph/node/${encodeURIComponent(nodeId)}`);
}

/* ---------------------------------------------------------------- 题卡解析 */

/**
 * 题卡「看答案解析」。
 * 后端接口按约定为 POST /api/quiz/explain，body {chunk_id}；
 * 返回形状未定，这里保留原始对象，由画布做防御式渲染。
 */
export async function explainQuiz(chunkId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>('/api/quiz/explain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chunk_id: chunkId }),
  });
}

/* ---------------------------------------------------------------- 错题本 */

export interface WrongbookPayload {
  question: string;
  wrong_answer: string;
  root_cause: string;
  trace_ref: string;
  correct: string;
  pitfall: string;
  kp_ids: string[];
  source: string;
}

/** 写操作带 X-Account，保证记到当前登录账号名下。 */
export async function addWrongbook(
  payload: WrongbookPayload,
  account: string,
): Promise<{ ok: boolean; id: string }> {
  return request<{ ok: boolean; id: string }>('/api/wrongbook', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Account': account },
    body: JSON.stringify(payload),
  });
}

export async function getWrongbook(
  account: string,
): Promise<{ items: Record<string, unknown>[] }> {
  return request<{ items: Record<string, unknown>[] }>('/api/wrongbook', {
    headers: { 'X-Account': account },
  });
}
