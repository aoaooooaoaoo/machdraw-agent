import { useEffect, useState } from 'react';
import { getReview, type ReviewItem } from '../lib/api';
import { useAppStore } from '../lib/store';
import { toast } from '../lib/ui';
import { Icon } from './Icons';

/**
 * 今日复习（FSRS-lite）：按掌握度 + 最近练习时间列出到期知识点。
 * 点「复习这个」→ 切到知识图谱模块并发起一次针对性复习提问。
 */
export function ReviewDrawer() {
  const open = useAppStore((s) => s.reviewOpen);
  const setOpen = useAppStore((s) => s.setReviewOpen);
  const account = useAppStore((s) => s.account);
  const setActiveFeature = useAppStore((s) => s.setActiveFeature);
  const send = useAppStore((s) => s.send);
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !account) return;
    let alive = true;
    setLoading(true);
    getReview(account)
      .then((res) => {
        if (!alive) return;
        setItems(res.due || []);
        setTotal(res.total_tracked || 0);
      })
      .catch(() => toast('读取复习计划失败', 'error'))
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [open, account]);

  if (!open) return null;

  function reviewOne(item: ReviewItem) {
    setActiveFeature('graph');
    void send(`请帮我复习「${item.label}」：先问我一个关键问题，再按我的回答补充讲解，最后给出处。`);
    setOpen(false);
    toast('已发起复习追问');
  }

  return (
    <div className="history-mask" onClick={() => setOpen(false)}>
      <aside className="history-drawer review-drawer" onClick={(e) => e.stopPropagation()} aria-label="今日复习">
        <div className="history-head">
          <div>
            <div className="history-title">今日复习</div>
            <div className="history-sub">
              {loading ? '正在计算…' : `共跟踪 ${total} 个知识点 · ${items.length} 个到期`}
            </div>
          </div>
          <button className="icon-btn" type="button" aria-label="关闭复习" onClick={() => setOpen(false)}>
            <Icon name="x" size={16} />
          </button>
        </div>

        {!loading && items.length === 0 && (
          <div className="history-state">
            <Icon name="check" size={14} /> 今天没有到期的知识点。做题或自评后再来看看。
          </div>
        )}

        <div className="history-list">
          {items.map((it) => (
            <div key={it.key} className="review-item">
              <div className="review-main">
                <div className="review-label">{it.label}</div>
                <div className="review-meta">
                  <span className={`review-state is-${it.state === '需复习' ? 'again' : it.state === '已掌握' ? 'got' : 'learning'}`}>
                    {it.state}
                  </span>
                  <span>掌握度 {Math.round(it.score * 100)}%</span>
                  <span>逾期 {it.overdue_days} 天</span>
                </div>
              </div>
              <button className="btn btn-ghost btn-xs" type="button" onClick={() => reviewOne(it)}>
                复习这个
              </button>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
