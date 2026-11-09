/**
 * 轻量 UI 基础设施：toast 通知 + 复制到剪贴板。
 *
 * 不引第三方 UI 库（项目本来就是零 UI 依赖），用 20 行订阅式 store 实现；
 * 任何组件都能 `toast('已复制')`，由 <ToastViewport/> 统一渲染。
 */

export type ToastKind = 'info' | 'success' | 'error';

export interface ToastItem {
  id: number;
  text: string;
  kind: ToastKind;
}

type Listener = (items: ToastItem[]) => void;

let seq = 0;
let items: ToastItem[] = [];
const listeners = new Set<Listener>();

function emit(): void {
  for (const fn of listeners) fn(items);
}

export function subscribeToasts(fn: Listener): () => void {
  listeners.add(fn);
  fn(items);
  return () => {
    listeners.delete(fn);
  };
}

export function toast(text: string, kind: ToastKind = 'success'): void {
  const id = (seq += 1);
  items = [...items.slice(-3), { id, text, kind }];
  emit();
  window.setTimeout(() => {
    items = items.filter((t) => t.id !== id);
    emit();
  }, 2600);
}

/** 复制文本；Clipboard API 不可用（http/旧浏览器）时退回 textarea + execCommand。 */
export async function copyText(text: string, okMessage = '已复制'): Promise<boolean> {
  const value = String(text ?? '');
  if (!value.trim()) {
    toast('没有可复制的内容', 'info');
    return false;
  }
  try {
    if (navigator.clipboard && window.isSecureContext) {
      // 某些浏览器/无头环境里 clipboard.writeText 会一直 pending；加超时兜底，避免"点了没反应"
      await Promise.race([
        navigator.clipboard.writeText(value),
        new Promise((_, reject) => window.setTimeout(() => reject(new Error('clipboard-timeout')), 800)),
      ]);
      toast(okMessage);
      return true;
    }
  } catch {
    /* 继续走 fallback */
  }
  try {
    const ta = document.createElement('textarea');
    ta.value = value;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    if (ok) {
      toast(okMessage);
      return true;
    }
    toast('复制失败，请手动选择文本', 'error');
    return false;
  } catch {
    toast('复制失败，请手动选择文本', 'error');
    return false;
  }
}

/** 平台相关的快捷键文案。 */
export const IS_MAC = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);
export const MOD_KEY = IS_MAC ? '⌘' : 'Ctrl';
