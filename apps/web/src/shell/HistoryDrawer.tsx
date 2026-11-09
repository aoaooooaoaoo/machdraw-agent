import { useEffect, useRef, useState } from 'react';
import { getHistory, getHistoryDetail } from '../lib/api';
import { exportLearningData, importLearningData } from '../lib/backup';
import { useAppStore } from '../lib/store';
import { toast } from '../lib/ui';
import { Icon } from './Icons';

interface Row {
  id: string;
  module_key: string;
  title: string;
  updated_at: number;
  count: number;
}

/**
 * 历史会话抽屉：后端每轮问答已经落库（conversations/messages），
 * 这里只是把已有数据取回来；点一条会替换当前模块的会话内容。
 */
export function HistoryDrawer() {
  const open = useAppStore((s) => s.historyOpen);
  const setOpen = useAppStore((s) => s.setHistoryOpen);
  const account = useAppStore((s) => s.account);
  const modules = useAppStore((s) => s.modules);
  const loadConversation = useAppStore((s) => s.loadConversation);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open || !account) return;
    let alive = true;
    setLoading(true);
    setError(null);
    getHistory(account)
      .then((res) => {
        if (alive) setRows(res.conversations || []);
      })
      .catch((err) => {
        if (alive) setError((err as Error)?.message || String(err));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [open, account]);

  if (!open) return null;

  async function load(id: string) {
    if (!account) return;
    setLoadingId(id);
    try {
      const res = await getHistoryDetail(id, account);
      const row = rows.find((r) => r.id === id);
      const feature = row?.module_key || '__global__';
      loadConversation(feature, res.messages || [], res.artifacts || []);
      toast('已载入历史会话');
    } catch (err) {
      toast(`载入失败：${(err as Error)?.message || String(err)}`, 'error');
    } finally {
      setLoadingId(null);
    }
  }

  function moduleName(key: string): string {
    return modules.find((m) => m.id === key)?.name ?? key;
  }

  return (
    <div className="history-mask" onClick={() => setOpen(false)}>
      <aside className="history-drawer" onClick={(e) => e.stopPropagation()} aria-label="历史会话">
        <div className="history-head">
          <div>
            <div className="history-title">历史会话</div>
            <div className="history-sub">后端已按天保存 · 点一条恢复到工作台</div>
          </div>
          <button className="icon-btn" type="button" aria-label="关闭历史" onClick={() => setOpen(false)}>
            <Icon name="x" size={16} />
          </button>
        </div>

        {loading && <div className="history-state"><span className="spinner" /> 正在读取…</div>}
        {error && (
          <div className="history-state is-error">
            <Icon name="alert" size={14} />
            {error}
          </div>
        )}
        {!loading && !error && rows.length === 0 && (
          <div className="history-state">还没有历史会话。先问一个问题吧。</div>
        )}

        <div className="history-list">
          {rows.map((r) => (
            <button
              key={r.id}
              type="button"
              className="history-item"
              disabled={loadingId === r.id}
              onClick={() => void load(r.id)}
            >
              <div className="history-item-top">
                <span className="history-module">{moduleName(r.module_key)}</span>
                <span className="history-count">{r.count} 条</span>
              </div>
              <div className="history-item-title">{r.title}</div>
              <div className="history-item-time">
                {new Date(r.updated_at * 1000).toLocaleString('zh-CN', { hour12: false })}
                {loadingId === r.id && <span className="history-loading">载入中…</span>}
              </div>
            </button>
          ))}
        </div>

        <div className="history-foot">
          <div className="history-foot-hint">换设备/重启前，可把学习数据导出成 JSON；导入只增不减。</div>
          <div className="history-foot-actions">
            <button
              className="btn btn-ghost btn-xs"
              type="button"
              disabled={busy || !account}
              onClick={() => {
                if (!account) return;
                setBusy(true);
                exportLearningData(account)
                  .then(() => toast('备份已下载'))
                  .catch((err) => toast(`导出失败：${(err as Error)?.message || err}`, 'error'))
                  .finally(() => setBusy(false));
              }}
            >
              导出备份
            </button>
            <button
              className="btn btn-ghost btn-xs"
              type="button"
              disabled={busy || !account}
              onClick={() => importRef.current?.click()}
            >
              导入备份
            </button>
            <input
              ref={importRef}
              type="file"
              accept="application/json,.json"
              className="hidden-input"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = '';
                if (!file || !account) return;
                setBusy(true);
                importLearningData(file, account)
                  .then((res) => {
                    toast(`导入完成：掌握度 ${res.importedMastery} 条，错题 ${res.importedWrongbook} 条`);
                    window.setTimeout(() => window.location.reload(), 900);
                  })
                  .catch((err) => toast(`导入失败：${(err as Error)?.message || err}`, 'error'))
                  .finally(() => setBusy(false));
              }}
            />
          </div>
        </div>
      </aside>
    </div>
  );
}
