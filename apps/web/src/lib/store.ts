/**
 * 全局状态（Zustand）。
 *
 * 选 Zustand 而不是 useReducer 的理由：
 *  - 工作台里"右栏按钮写中栏输入框""左栏切模块要同时改会话/画布/顶栏"这类跨子树写入很多，
 *    用 context + reducer 会把 provider 层层包进三栏；Zustand 的 store 直接裸用，组件各自订阅。
 *  - 流式 token 每帧都要更新一条消息，Zustand 的选择器订阅能把重渲染限制在消息流与状态栏，
 *    不需要把整个 App 放进一个 reducer 里重渲染。
 *  - 会话按模块分片存，天然是"对象 key 索引"，reducer 的 switch 反而更啰嗦。
 */
import { create } from 'zustand';
import { getHealth, getModules, login as apiLogin, ApiError } from './api';
import { streamChat, ChatHTTPError } from './sse';
import { hasCanvasOwner } from '../modules/registry';
import type {
  ArtifactState,
  ArtifactType,
  ChatMessage,
  ChatRequestBody,
  DoneMeta,
  HealthInfo,
  ModuleManifest,
  SSEEvent,
  ToolCallState,
} from './types';

const ACCOUNT_KEY = 'rp.account';
const GLOBAL_SESSION_ID = '__global__';

function newId(prefix: string): string {
  const rand =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(16).slice(2, 10);
  return `${prefix}_${Date.now().toString(36)}_${rand}`;
}

function readAccount(): string | null {
  try {
    return localStorage.getItem(ACCOUNT_KEY);
  } catch {
    return null;
  }
}

function writeAccount(account: string | null): void {
  try {
    if (account) localStorage.setItem(ACCOUNT_KEY, account);
    else localStorage.removeItem(ACCOUNT_KEY);
  } catch {
    /* 隐私模式忽略 */
  }
}

export interface SessionStats {
  messages: number;
  evidences: number;
  coverage: number;
  ms: number;
  frames: number;
}

export interface SessionState {
  id: string;
  messages: ChatMessage[];
  /** 本轮收到的画布 artifact（一次问答可能有多个，如 graph + evidence），按到达顺序。 */
  artifacts: ArtifactState[];
  stats: SessionStats;
  draft: string;
  streaming: boolean;
}

function emptySession(id: string): SessionState {
  return {
    id,
    messages: [],
    artifacts: [],
    stats: { messages: 0, evidences: 0, coverage: 0, ms: 0, frames: 0 },
    draft: '',
    streaming: false,
  };
}

/** 取最近一个 evidence artifact（证据段数与覆盖率的口径都来自它）。 */
function latestEvidence(artifacts: ArtifactState[]): ArtifactState | undefined {
  for (let i = artifacts.length - 1; i >= 0; i -= 1) {
    if (artifacts[i].artifactType === 'evidence') return artifacts[i];
  }
  return undefined;
}

/** 统计口径：证据段数取本轮最近的 evidence artifact；覆盖率优先 artifact，其次 done 帧。 */
function recomputeStats(session: SessionState): SessionStats {
  const evidence = latestEvidence(session.artifacts);
  let evidences = session.stats.evidences;
  if (evidence) {
    const list = evidence.data?.evidences;
    if (Array.isArray(list)) evidences = list.length;
  }
  const cov = evidence?.data?.coverage;
  const coverage = typeof cov === 'number' ? cov : session.stats.coverage;
  const ms = session.stats.ms;
  const frames = session.messages.reduce((sum, m) => sum + (m.frames || 0), 0);
  return { messages: session.messages.length, evidences, coverage, ms, frames };
}

function num(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

/** 前端追加的系统提示（不发给后端；role='system' 会在历史过滤里被排除）。 */
function makeNotice(content: string): ChatMessage {
  return {
    id: newId('sys'),
    role: 'system',
    content,
    thinking: '',
    tools: [],
    streaming: false,
    frames: 0,
  };
}

function unknownArtifactNotice(types: string[]): ChatMessage {
  const list = types.map((t) => `\`${t}\``).join('、');
  return makeNotice(
    `> ⚠️ **系统提示**：该产物类型暂无画布（${list}），已跳过画布展示。\n>\n` +
      '> 请检查后端工具的 `artifact_type` 是否写错，或前端是否缺少 `features/<id>/index.ts` 注册。',
  );
}

/**
 * 兜底：历史/内存里的 artifact 如果已经没人认领（模块被删/改名），
 * 丢掉这些画布并补一条提示，避免右栏打开一个永久占位或白屏。
 */
function restoreKnownArtifacts(session: SessionState): SessionState {
  const unknown = Array.from(
    new Set(session.artifacts.filter((a) => !hasCanvasOwner(a.artifactType)).map((a) => a.artifactType)),
  );
  if (unknown.length === 0) return session;
  return {
    ...session,
    artifacts: session.artifacts.filter((a) => hasCanvasOwner(a.artifactType)),
    messages: [...session.messages, unknownArtifactNotice(unknown)],
  };
}

let activeAbort: AbortController | null = null;

export interface AppStore {
  account: string | null;
  backendOnline: boolean | null;
  health: HealthInfo | null;
  modules: ModuleManifest[];
  modulesError: string | null;
  bootstrapped: boolean;
  bootstrapping: boolean;
  activeFeature: string;
  sessions: Record<string, SessionState>;
  globalError: string | null;

  bootstrap: () => Promise<void>;
  signIn: (account: string, password: string) => Promise<void>;
  signOut: () => void;
  refreshHealth: () => Promise<void>;
  setActiveFeature: (id: string) => void;
  setDraft: (text: string) => void;
  send: (text?: string) => Promise<void>;
  stop: () => void;
  dismissGlobalError: () => void;
}

export const useAppStore = create<AppStore>()((set, get) => {
  /** 改某一个会话的字段（其余会话原样保留）。 */
  function patchSession(id: string, patch: (s: SessionState) => SessionState): void {
    set((state) => {
      const current = state.sessions[id] ?? emptySession(id);
      return { sessions: { ...state.sessions, [id]: patch(current) } };
    });
  }

  function patchAssistant(featureId: string, msgId: string, fn: (m: ChatMessage) => ChatMessage): void {
    patchSession(featureId, (s) => ({
      ...s,
      messages: s.messages.map((m) => (m.id === msgId ? fn(m) : m)),
    }));
  }

  function applyEvent(featureId: string, msgId: string, ev: SSEEvent): void {
    patchSession(featureId, (session) => {
      const idx = session.messages.findIndex((m) => m.id === msgId);
      if (idx < 0) return session;
      const msg = { ...session.messages[idx], frames: session.messages[idx].frames + 1 };
      let nextArtifacts = session.artifacts;
      let doneStats: Partial<SessionStats> | null = null;
      const notices: ChatMessage[] = [];

      switch (ev.type) {
        case 'thinking':
          msg.thinking = msg.thinking + (ev.text || '');
          break;
        case 'token':
          msg.content = msg.content + (ev.text || '');
          break;
        case 'tool_call': {
          const callId = ev.id || newId('call');
          const tool: ToolCallState = {
            id: callId,
            name: ev.name || 'unknown',
            label: ev.label || ev.name || '工具调用',
            args: (ev.args as Record<string, unknown>) || {},
            status: 'running',
            summary: '',
            detail: '',
          };
          msg.tools = [...msg.tools, tool];
          break;
        }
        case 'tool_result': {
          const callId = ev.id || '';
          const exists = msg.tools.some((t) => t.id === callId);
          if (exists) {
            msg.tools = msg.tools.map((t) =>
              t.id === callId
                ? { ...t, status: 'done', summary: ev.summary || '', detail: ev.detail || '' }
                : t,
            );
          } else {
            msg.tools = [
              ...msg.tools,
              {
                id: callId || newId('call'),
                name: ev.name || 'unknown',
                label: ev.name || '工具结果',
                args: {},
                status: 'done',
                summary: ev.summary || '',
                detail: ev.detail || '',
              },
            ];
          }
          break;
        }
        case 'artifact': {
          if (ev.artifactType) {
            // ★ 兜底：没人认领的 artifactType 不挂画布，也不静默丢弃 ——
            //   在对话流里补一条系统提示，方便定位「工具类型写错 / 模块没注册」。
            if (!hasCanvasOwner(ev.artifactType)) {
              notices.push(unknownArtifactNotice([ev.artifactType]));
              break;
            }
            const artifact: ArtifactState = {
              artifactType: ev.artifactType as ArtifactType,
              data: (ev.data as Record<string, any>) || {},
              receivedAt: Date.now(),
            };
            msg.artifact = artifact;
            // 一次问答可能推多个画布（如 graph + evidence），保留本轮全部，右栏用标签页切换
            nextArtifacts = [...nextArtifacts, artifact].slice(-8);
          }
          break;
        }
        case 'error':
          msg.error = ev.text || ev.code || '未知错误';
          msg.streaming = false;
          break;
        case 'done': {
          msg.meta = ((ev.data || {}) as DoneMeta) ?? undefined;
          msg.streaming = false;
          doneStats = {
            evidences: num(ev.data?.evidence) ?? session.stats.evidences,
            coverage: num(ev.data?.coverage) ?? session.stats.coverage,
            ms: num(ev.data?.ms) ?? session.stats.ms,
          };
          break;
        }
        default:
          break;
      }

      const messages = [...session.messages];
      messages[idx] = msg;
      messages.push(...notices);
      const next: SessionState = {
        ...session,
        messages,
        artifacts: nextArtifacts,
        stats: { ...session.stats, ...(doneStats || {}) },
      };
      next.stats = recomputeStats(next);
      return next;
    });
  }

  return {
    account: readAccount(),
    backendOnline: null,
    health: null,
    modules: [],
    modulesError: null,
    bootstrapped: false,
    bootstrapping: false,
    activeFeature: GLOBAL_SESSION_ID,
    sessions: { [GLOBAL_SESSION_ID]: emptySession(GLOBAL_SESSION_ID) },
    globalError: null,

    bootstrap: async () => {
      // React 19 StrictMode 开发期会跑两遍 effect，这里做幂等保护
      if (get().bootstrapping || get().bootstrapped) return;
      set({ bootstrapping: true });
      const account = readAccount();
      set({ account });
      const tasks: Promise<void>[] = [get().refreshHealth()];
      tasks.push(
        (async () => {
          try {
            const modules = await getModules();
            set({ modules, modulesError: null });
            // 默认进全局对话；如果当前 feature 不在列表里，回落到第一个模块
            const ids = new Set(modules.map((m) => m.id));
            const cur = get().activeFeature;
            if (!ids.has(cur) && modules.length > 0) {
              set({ activeFeature: modules[0].id });
            }
          } catch (err) {
            set({ modulesError: err instanceof ApiError ? err.message : String(err) });
          }
        })(),
      );
      await Promise.allSettled(tasks);
      // 确保当前激活模块有会话
      const active = get().activeFeature;
      if (!get().sessions[active]) {
        set((state) => ({ sessions: { ...state.sessions, [active]: emptySession(active) } }));
      }
      set({ bootstrapping: false, bootstrapped: true });
    },

    signIn: async (account, password) => {
      const result = await apiLogin(account.trim(), password);
      writeAccount(result.account);
      set({ account: result.account, globalError: null });
      await get().refreshHealth();
    },

    signOut: () => {
      activeAbort?.abort();
      activeAbort = null;
      writeAccount(null);
      set({
        account: null,
        sessions: { [GLOBAL_SESSION_ID]: emptySession(GLOBAL_SESSION_ID) },
        activeFeature: GLOBAL_SESSION_ID,
      });
    },

    refreshHealth: async () => {
      try {
        const health = await getHealth();
        set({ health, backendOnline: health.ok !== false });
      } catch {
        set({ backendOnline: false, health: null });
      }
    },

    setActiveFeature: (id) => {
      set((state) => {
        const current = state.sessions[id];
        const sessions = current
          ? { ...state.sessions, [id]: restoreKnownArtifacts(current) }
          : { ...state.sessions, [id]: emptySession(id) };
        return { activeFeature: id, sessions };
      });
    },

    setDraft: (text) => {
      const featureId = get().activeFeature;
      patchSession(featureId, (s) => ({ ...s, draft: text }));
    },

    send: async (text) => {
      const featureId = get().activeFeature;
      const session = get().sessions[featureId] ?? emptySession(featureId);
      const content = (text ?? session.draft).trim();
      if (!content) return;
      if (session.streaming) return;

      const account = get().account;
      if (!account) {
        set({ globalError: '请先登录再提问' });
        return;
      }

      const userMsg: ChatMessage = {
        id: newId('u'),
        role: 'user',
        content,
        thinking: '',
        tools: [],
        streaming: false,
        frames: 0,
      };
      const assistantMsg: ChatMessage = {
        id: newId('a'),
        role: 'assistant',
        content: '',
        thinking: '',
        tools: [],
        streaming: true,
        frames: 0,
      };

      const history: ChatRequestBody['messages'] = [...session.messages, userMsg]
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .filter((m) => !(m.role === 'assistant' && !m.content && !m.error))
        .map((m) => ({ role: m.role, content: m.content }));

      set((state) => {
        const s = state.sessions[featureId] ?? emptySession(featureId);
        const nextMessages = [...s.messages, userMsg, assistantMsg];
        const next: SessionState = {
          ...s,
          messages: nextMessages,
          // 新一轮问答：画布与统计都按本轮重算（canvas 展示本轮 artifact）
          artifacts: [],
          draft: '',
          streaming: true,
          stats: {
            ...s.stats,
            messages: nextMessages.length,
            evidences: 0,
            coverage: 0,
            ms: 0,
          },
        };
        return { sessions: { ...state.sessions, [featureId]: next }, globalError: null };
      });

      const controller = new AbortController();
      activeAbort = controller;

      // 模块身份：按参考作品契约发 {id, title, persona} 对象，
      // 后端据此拼进系统提示词 —— 这样新增模块不需要改后端。
      const mod = featureId === GLOBAL_SESSION_ID
        ? null
        : get().modules.find((m) => m.id === featureId);
      const featureRef = mod
        ? { id: mod.id, title: mod.name, persona: mod.system_prompt || mod.desc || '' }
        : (featureId === GLOBAL_SESSION_ID ? null : featureId);

      const body: ChatRequestBody = {
        session_id: `local:${featureId}`,
        messages: history,
        feature: featureRef,
      };

      try {
        await streamChat(body, {
          account,
          signal: controller.signal,
          onEvent: (ev) => applyEvent(featureId, assistantMsg.id, ev),
        });
      } catch (err) {
        const aborted = controller.signal.aborted || (err as Error)?.name === 'AbortError';
        let message: string;
        if (aborted) {
          message = '已手动停止生成';
        } else if (err instanceof ChatHTTPError) {
          message = err.message;
        } else if (err instanceof ApiError) {
          message = err.message;
        } else {
          message = `对话失败：${(err as Error)?.message || String(err)}`;
        }
        if (!aborted) {
          set({ backendOnline: false });
        }
        patchAssistant(featureId, assistantMsg.id, (m) => ({
          ...m,
          error: message,
          streaming: false,
        }));
        // 即使出错也要把状态收尾，避免界面卡在"生成中"
        patchSession(featureId, (s) => ({ ...s, streaming: false }));
      } finally {
        if (activeAbort === controller) activeAbort = null;
        patchSession(featureId, (s) => ({
          ...s,
          streaming: false,
          messages: s.messages.map((m) =>
            m.id === assistantMsg.id ? { ...m, streaming: false } : m,
          ),
        }));
        const finished = get().sessions[featureId];
        if (finished) {
          patchSession(featureId, (s) => ({ ...s, stats: recomputeStats(s) }));
        }
      }
    },

    stop: () => {
      activeAbort?.abort();
      activeAbort = null;
    },

    dismissGlobalError: () => set({ globalError: null }),
  };
});

/**
 * 当前会话（派生选择器）。
 * 注意用模块级稳定兜底对象：Zustand v5 基于 useSyncExternalStore，
 * 每次 getSnapshot 返回新对象会导致无限重渲染。
 */
const FALLBACK_SESSION: SessionState = emptySession('__fallback__');

export function useActiveSession(): SessionState {
  return useAppStore((s) => s.sessions[s.activeFeature] ?? FALLBACK_SESSION);
}
