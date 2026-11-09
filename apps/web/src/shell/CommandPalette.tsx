import { useEffect, useMemo, useRef, useState } from 'react';
import { useAppStore } from '../lib/store';
import { copyText, MOD_KEY, toast } from '../lib/ui';
import { Icon } from './Icons';

interface PaletteItem {
  id: string;
  group: string;
  icon: string;
  title: string;
  hint?: string;
  run: () => void;
  keywords?: string;
}

/**
 * 命令面板（Ctrl/⌘ + K）：
 *  - 切换模块、发预设问题、新会话、打开教师端、复制课程统计；
 *  - 键盘 ↑↓ 选择 / Enter 执行 / Esc 关闭；
 *  - 打开时自动聚焦输入框，输入即过滤（标题 + 关键词）。
 */
export function CommandPalette() {
  const open = useAppStore((s) => s.paletteOpen);
  const setOpen = useAppStore((s) => s.setPaletteOpen);
  const modules = useAppStore((s) => s.modules);
  const activeFeature = useAppStore((s) => s.activeFeature);
  const setActiveFeature = useAppStore((s) => s.setActiveFeature);
  const send = useAppStore((s) => s.send);
  const clearSession = useAppStore((s) => s.clearSession);
  const setHistoryOpen = useAppStore((s) => s.setHistoryOpen);
  const setReviewOpen = useAppStore((s) => s.setReviewOpen);
  const setNotesOpen = useAppStore((s) => s.setNotesOpen);
  const health = useAppStore((s) => s.health);

  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const close = () => {
    setOpen(false);
  };

  const items = useMemo<PaletteItem[]>(() => {
    const out: PaletteItem[] = [];

    for (const m of modules) {
      out.push({
        id: `module:${m.id}`,
        group: '切换模块',
        icon: m.icon || 'chat',
        title: m.name,
        hint: m.desc,
        keywords: `${m.id} ${m.name} ${m.desc ?? ''} ${(m.entry_examples ?? []).join(' ')}`,
        run: () => {
          setActiveFeature(m.id);
          close();
        },
      });
    }

    for (const m of modules) {
      for (const ex of m.entry_examples ?? []) {
        out.push({
          id: `ask:${m.id}:${ex}`,
          group: '直接提问',
          icon: 'spark',
          title: ex,
          hint: `${m.name} · 点击即发送`,
          keywords: `${m.name} ${ex}`,
          run: () => {
            void send(ex);
            close();
          },
        });
      }
    }

    out.push(
      {
        id: 'action:notes',
        group: '操作',
        icon: 'note',
        title: '打开便签笔记',
        hint: '可拖拽、自动保存、支持 Markdown / 公式',
        keywords: '便签 笔记 note 备忘',
        run: () => {
          setNotesOpen(true);
          close();
        },
      },
      {
        id: 'action:history',
        group: '操作',
        icon: 'history',
        title: '打开历史会话',
        hint: '后端已按天保存，可恢复到工作台',
        keywords: '历史 会话 记录 history',
        run: () => {
          setHistoryOpen(true);
          close();
        },
      },
      {
        id: 'action:review',
        group: '操作',
        icon: 'target',
        title: '今日复习',
        hint: '按掌握度 + 时间列出到期知识点',
        keywords: '复习 计划 到期 review',
        run: () => {
          setReviewOpen(true);
          close();
        },
      },
      {
        id: 'action:new-session',
        group: '操作',
        icon: 'refresh',
        title: '开始新会话',
        hint: '清空当前模块的对话与画布',
        keywords: '新会话 清空 重置 new session clear',
        run: () => {
          clearSession();
          toast('已开始新会话');
          close();
        },
      },
      {
        id: 'action:copy-health',
        group: '操作',
        icon: 'copy',
        title: '复制课程运行信息',
        hint: '语料块数 / 图谱规模 / 门控阈值',
        keywords: '复制 统计 health 信息',
        run: () => {
          const text = health
            ? `核反应堆物理 AI 助教\n语料：${health.chunks} 块 / ${health.docs} 文档\n图谱：${health.nodes} 节点 / ${health.edges} 边\n门控 τ=${health.gate_tau}\n工具：${health.tools?.length ?? 0} 个`
            : '核反应堆物理 AI 助教（后端信息尚未加载）';
          void copyText(text, '运行信息已复制');
          close();
        },
      },
      {
        id: 'action:admin',
        group: '操作',
        icon: 'book',
        title: '打开教师端看板',
        hint: '语料清单 / 学情看板 / 待复核条目',
        keywords: '教师 admin 看板 teacher',
        run: () => {
          window.open('/admin', '_blank', 'noopener');
          close();
        },
      },
      {
        id: 'action:focus',
        group: '操作',
        icon: 'pencil',
        title: '把焦点放回输入框',
        hint: '快捷键 Ctrl /',
        keywords: '输入 聚焦 focus composer',
        run: () => {
          close();
          window.setTimeout(() => {
            document.querySelector<HTMLTextAreaElement>('.composer-input')?.focus();
          }, 30);
        },
      },
    );

    return out;
  }, [modules, health, send, setActiveFeature, clearSession, setOpen, setHistoryOpen, setReviewOpen, setNotesOpen]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => `${it.title} ${it.hint ?? ''} ${it.keywords ?? ''}`.toLowerCase().includes(q));
  }, [items, query]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setIndex(0);
      window.setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  useEffect(() => {
    setIndex(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        close();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${index}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [index]);

  if (!open) return null;

  const groups = [...new Set(filtered.map((it) => it.group))];
  const flat = filtered;
  const active = flat[Math.min(index, Math.max(0, flat.length - 1))];

  return (
    <div className="palette-mask" role="dialog" aria-modal="true" aria-label="命令面板" onClick={close}>
      <div className="palette" onClick={(e) => e.stopPropagation()}>
        <div className="palette-search">
          <Icon name="search" size={17} />
          <input
            ref={inputRef}
            value={query}
            placeholder="搜索模块、问题或操作…"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault();
                setIndex((i) => Math.min(flat.length - 1, i + 1));
              } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setIndex((i) => Math.max(0, i - 1));
              } else if (e.key === 'Enter') {
                e.preventDefault();
                active?.run();
              }
            }}
            aria-label="搜索模块、问题或操作"
          />
          <kbd className="palette-kbd">Esc</kbd>
        </div>

        <div className="palette-list" ref={listRef}>
          {groups.map((group) => (
            <div key={group} className="palette-group">
              <div className="palette-group-title">{group}</div>
              {filtered
                .filter((it) => it.group === group)
                .map((it) => {
                  const idx = flat.indexOf(it);
                  return (
                    <button
                      key={it.id}
                      type="button"
                      data-idx={idx}
                      className={`palette-item ${idx === index ? 'is-active' : ''}`}
                      onMouseEnter={() => setIndex(idx)}
                      onClick={() => it.run()}
                    >
                      <span className="palette-item-icon">
                        <Icon name={it.icon} size={15} />
                      </span>
                      <span className="palette-item-text">
                        <span className="palette-item-title">{it.title}</span>
                        {it.hint && <span className="palette-item-hint">{it.hint}</span>}
                      </span>
                      {activeFeature && it.id === `module:${activeFeature}` && (
                        <span className="palette-item-badge">当前</span>
                      )}
                    </button>
                  );
                })}
            </div>
          ))}
          {flat.length === 0 && (
            <div className="palette-empty">
              <Icon name="search" size={18} />
              <p>没有匹配的模块或问题，换个关键词试试。</p>
            </div>
          )}
        </div>

        <div className="palette-foot">
          <span>
            <kbd>↑</kbd>
            <kbd>↓</kbd> 选择
          </span>
          <span>
            <kbd>Enter</kbd> 执行
          </span>
          <span>
            <kbd>Esc</kbd> 关闭
          </span>
          <span className="palette-foot-right">
            <kbd>{MOD_KEY}</kbd>+<kbd>K</kbd> 随时打开
          </span>
        </div>
      </div>
    </div>
  );
}
