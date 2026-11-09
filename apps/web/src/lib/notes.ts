/** 便签卡片：按账号存 localStorage（位置、内容、颜色、折叠/预览状态）。 */
export interface StickyNote {
  id: string;
  text: string;
  x: number;
  y: number;
  color: string;
  collapsed?: boolean;
  preview?: boolean;
  updatedAt: number;
}

const KEY = 'rp.notes.v1';
const COLORS = ['yellow', 'pink', 'blue', 'green', 'purple'];

function accountKey(account: string | null): string {
  return `${KEY}:${account || 'guest'}`;
}

export function noteColors(): string[] {
  return COLORS;
}

export function loadNotes(account: string | null): StickyNote[] {
  try {
    const raw = localStorage.getItem(accountKey(account));
    const data = raw ? JSON.parse(raw) : [];
    return Array.isArray(data)
      ? data.filter((n) => n && typeof n.id === 'string' && typeof n.text === 'string')
      : [];
  } catch {
    return [];
  }
}

export function saveNotes(account: string | null, notes: StickyNote[]): void {
  try {
    localStorage.setItem(accountKey(account), JSON.stringify(notes.slice(0, 12)));
  } catch {
    /* 配额/隐私模式忽略 */
  }
}

export function makeNote(index: number): StickyNote {
  const vw = typeof window !== 'undefined' ? window.innerWidth : 1200;
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
  const x = Math.max(16, Math.min(vw - 320, vw - 330 - index * 26));
  const y = Math.max(80, Math.min(vh - 300, 110 + index * 26));
  return {
    id: `note_${Date.now().toString(36)}_${Math.random().toString(16).slice(2, 6)}`,
    text: '',
    x,
    y,
    color: COLORS[index % COLORS.length],
    updatedAt: Date.now(),
  };
}
