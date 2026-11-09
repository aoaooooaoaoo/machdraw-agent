import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../lib/store';
import { loadNotes, makeNote, noteColors, saveNotes, type StickyNote } from '../lib/notes';
import { Icon } from './Icons';
import { Markdown } from './Markdown';

/**
 * 可拖拽便签：浮在工作台上的自定义笔记。
 * - 拖动标题栏移动；位置/内容/颜色/折叠/预览状态按账号存 localStorage；
 * - 支持多条（右上「+」新建）、Markdown/KaTeX 预览、折叠、关闭；
 * - 不遮挡主流程：默认 z-index 低于命令面板/弹窗。
 */
export function StickyNotes() {
  const open = useAppStore((s) => s.notesOpen);
  const setOpen = useAppStore((s) => s.setNotesOpen);
  const account = useAppStore((s) => s.account);

  const [notes, setNotes] = useState<StickyNote[]>([]);
  const [loaded, setLoaded] = useState(false);
  const dragRef = useRef<{ id: string; dx: number; dy: number } | null>(null);

  // 打开 / 切账号时载入
  useEffect(() => {
    if (!open) return;
    setNotes(loadNotes(account));
    setLoaded(true);
  }, [open, account]);

  // 没有便签时自动建一张
  useEffect(() => {
    if (!open || !loaded) return;
    if (notes.length === 0) setNotes([makeNote(0)]);
  }, [open, loaded, notes.length]);

  // 自动保存（防抖）
  useEffect(() => {
    if (!open || !loaded) return;
    const t = window.setTimeout(() => saveNotes(account, notes), 400);
    return () => window.clearTimeout(t);
  }, [notes, account, open, loaded]);

  // 拖动：window 级 pointermove/up，比 header 局部事件更稳（触屏/鼠标都可用）
  useEffect(() => {
    function onMove(e: PointerEvent) {
      const d = dragRef.current;
      if (!d) return;
      const x = Math.min(Math.max(8, e.clientX - d.dx), window.innerWidth - 308);
      const y = Math.min(Math.max(60, e.clientY - d.dy), window.innerHeight - 48);
      setNotes((prev) => prev.map((n) => (n.id === d.id ? { ...n, x, y, updatedAt: Date.now() } : n)));
    }
    function onUp() {
      dragRef.current = null;
    }
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    };
  }, []);

  if (!open) return null;

  function patch(id: string, fn: (n: StickyNote) => StickyNote) {
    setNotes((prev) => prev.map((n) => (n.id === id ? { ...fn(n), updatedAt: Date.now() } : n)));
  }

  function addNote() {
    setNotes((prev) => [...prev, makeNote(prev.length)]);
  }

  function removeNote(id: string) {
    setNotes((prev) => {
      const next = prev.filter((n) => n.id !== id);
      if (next.length === 0) setOpen(false);
      return next;
    });
  }

  function onHeaderDown(e: React.PointerEvent<HTMLDivElement>, note: StickyNote) {
    if (e.button !== 0) return;
    const target = e.target as HTMLElement;
    if (target.closest('.sticky-tools')) return;
    e.preventDefault();
    dragRef.current = { id: note.id, dx: e.clientX - note.x, dy: e.clientY - note.y };
  }

  const colors = noteColors();

  return (
    <div className="sticky-layer" aria-label="便签">
      {notes.map((note) => (
        <section
          key={note.id}
          className={`sticky-note is-${note.color} ${note.collapsed ? 'is-collapsed' : ''}`}
          style={{ left: note.x, top: note.y }}
        >
          <div
            className="sticky-head"
            onPointerDown={(e) => onHeaderDown(e, note)}
          >
            <span className="sticky-title">
              <Icon name="note" size={14} />
              <span>笔记</span>
            </span>
            <div className="sticky-tools">
              <button
                type="button"
                title={note.collapsed ? '展开' : '折叠'}
                aria-label="折叠便签"
                onClick={() => patch(note.id, (n) => ({ ...n, collapsed: !n.collapsed }))}
              >
                <Icon name="chevron" size={14} className={note.collapsed ? '' : 'chev is-open'} />
              </button>
              <button
                type="button"
                title="切换颜色"
                aria-label="切换颜色"
                onClick={() =>
                  patch(note.id, (n) => {
                    const idx = colors.indexOf(n.color);
                    return { ...n, color: colors[(idx + 1) % colors.length] };
                  })
                }
              >
                <span className="sticky-color-dot" />
              </button>
              <button
                type="button"
                title={note.preview ? '编辑' : '预览（支持 Markdown / 公式）'}
                aria-label="切换预览"
                onClick={() => patch(note.id, (n) => ({ ...n, preview: !n.preview }))}
              >
                <Icon name="eye" size={14} />
              </button>
              <button type="button" title="新建便签" aria-label="新建便签" onClick={addNote}>
                <Icon name="plus" size={15} />
              </button>
              <button type="button" title="关闭这张便签" aria-label="关闭便签" onClick={() => removeNote(note.id)}>
                <Icon name="x" size={14} />
              </button>
            </div>
          </div>

          {!note.collapsed && (
            <div className="sticky-body">
              {note.preview ? (
                <div className="sticky-preview">
                  {note.text.trim() ? <Markdown text={note.text} /> : <span className="sticky-placeholder">（空笔记）</span>}
                </div>
              ) : (
                <textarea
                  className="sticky-textarea"
                  value={note.text}
                  placeholder="写点什么…支持 Markdown 和 $公式$，自动保存"
                  onChange={(e) => patch(note.id, (n) => ({ ...n, text: e.target.value }))}
                  onPointerDown={(e) => e.stopPropagation()}
                />
              )}
              <div className="sticky-foot">
                <span>{note.text.length} 字</span>
                <span>拖动标题栏移动</span>
              </div>
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
