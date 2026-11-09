import { useEffect, useState } from 'react';
import type { FeatureProps } from '../../lib/canvasFeature';
import type { PlanData } from '../../lib/api';
import { getPlan } from '../../lib/api';
import { useAppStore } from '../../lib/store';
import { toast } from '../../lib/ui';
import { Icon } from '../../shell/Icons';

const STATE_COLOR: Record<string, string> = {
  已掌握: '#16a34a',
  在学: '#d97706',
  需复习: '#dc2626',
  未学: '#94a3b8',
};

/**
 * 学习计划（整页模块）：
 *  - 今日任务：到期复习（FSRS-lite）
 *  - 下一步建议：按前置关系 + 掌握度推荐
 *  - 掌握度总览 + 快捷入口
 */
export function StudyPage(_props: FeatureProps) {
  const account = useAppStore((s) => s.account);
  const setActiveFeature = useAppStore((s) => s.setActiveFeature);
  const send = useAppStore((s) => s.send);
  const setReviewOpen = useAppStore((s) => s.setReviewOpen);
  const [data, setData] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(false);

  function load() {
    if (!account) return;
    setLoading(true);
    getPlan(account)
      .then(setData)
      .catch((err) => toast(`读取学习计划失败：${(err as Error)?.message || err}`, 'error'))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [account]);

  function goReview(label: string) {
    setActiveFeature('concept');
    void send(`请出 1 道关于「${label}」的题，先不要给答案；我做完后请你判分。`);
    toast('已切到概念辨析，开始复习');
  }

  function goLearn(label: string) {
    setActiveFeature('kbrag');
    void send(`请按「前置 → 定义 → 公式 → 例题 → 易错点」讲解「${label}」，并给出教材出处。`);
    toast('已切到教材溯源');
  }

  const counts = data?.counts || {};
  const tracked = data?.total_tracked || 0;
  const mastered = counts['已掌握'] || 0;
  const due = data?.due || [];
  const recs = data?.recommendations || [];

  return (
    <div className="study-page">
      <header className="study-head">
        <div>
          <h1>学习计划</h1>
          <p>按掌握度、到期复习和前置依赖，安排今天先学什么、先复习什么。</p>
        </div>
        <div className="study-head-actions">
          <button className="btn btn-ghost" type="button" onClick={load} disabled={loading}>
            <Icon name="refresh" size={14} /> 刷新
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() => {
              setActiveFeature('concept');
              void send('考我一道题');
            }}
          >
            <Icon name="spark" size={14} /> 出题练一练
          </button>
        </div>
      </header>

      <div className="study-stats">
        <div className="study-stat">
          <span className="study-stat-n">追踪知识点</span>
          <b>{tracked}</b>
        </div>
        <div className="study-stat is-got">
          <span className="study-stat-n">已掌握</span>
          <b>{mastered}</b>
        </div>
        <div className="study-stat is-learning">
          <span className="study-stat-n">在学</span>
          <b>{counts['在学'] || 0}</b>
        </div>
        <div className="study-stat is-again">
          <span className="study-stat-n">需复习</span>
          <b>{counts['需复习'] || 0}</b>
        </div>
        <div className="study-stat">
          <span className="study-stat-n">今日到期</span>
          <b>{due.length}</b>
        </div>
      </div>

      {tracked === 0 && !loading && (
        <div className="study-empty">
          <Icon name="target" size={26} />
          <h3>还没有学习记录</h3>
          <p>先做一道题，或在题卡里点「我会了 / 还不会」，这里就会自动生成计划。</p>
          <div className="study-empty-actions">
            <button className="btn btn-primary" type="button" onClick={() => { setActiveFeature('concept'); void send('考我一道题'); }}>
              去出题
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => setActiveFeature('graph')}>
              看知识图谱
            </button>
          </div>
        </div>
      )}

      {tracked > 0 && (
        <div className="study-cols">
          <section className="study-card">
            <div className="study-card-head">
              <h2>今日任务</h2>
              <span className="study-card-hint">到期 {due.length} 个</span>
            </div>
            {due.length === 0 ? (
              <div className="study-card-empty">
                <Icon name="check" size={16} /> 今天没有到期复习。可以做几道新题，或看看下一步建议。
              </div>
            ) : (
              <ul className="study-list">
                {due.map((it) => (
                  <li key={it.key} className="study-item">
                    <div className="study-item-main">
                      <div className="study-item-title">{it.label}</div>
                      <div className="study-item-meta">
                        <span className="study-badge" style={{ color: STATE_COLOR[it.state] || '#94a3b8' }}>
                          {it.state}
                        </span>
                        <span>掌握度 {Math.round(it.score * 100)}%</span>
                        <span>逾期 {it.overdue_days} 天</span>
                      </div>
                    </div>
                    <button className="btn btn-ghost btn-xs" type="button" onClick={() => goReview(it.label)}>
                      去复习
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="study-card">
            <div className="study-card-head">
              <h2>下一步建议</h2>
              <span className="study-card-hint">按前置关系推荐</span>
            </div>
            {recs.length === 0 ? (
              <div className="study-card-empty">暂时没有推荐；可以先去知识图谱里点一个知识点开始。</div>
            ) : (
              <ul className="study-list">
                {recs.map((it) => (
                  <li key={it.kp_id} className="study-item">
                    <div className="study-item-main">
                      <div className="study-item-title">
                        {it.label}
                        {it.chapter && <span className="study-chapter">{it.chapter}</span>}
                      </div>
                      <div className="study-item-meta">
                        <span className="study-badge" style={{ color: STATE_COLOR[it.state] || '#94a3b8' }}>
                          {it.state}
                        </span>
                        <span>{it.reason}</span>
                      </div>
                    </div>
                    <button className="btn btn-ghost btn-xs" type="button" onClick={() => goLearn(it.label)}>
                      去学习
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}

      <section className="study-quick">
        <button type="button" onClick={() => { setActiveFeature('wrongbook'); }}>
          <Icon name="alert" size={16} /> 错题本
        </button>
        <button type="button" onClick={() => setActiveFeature('graph')}>
          <Icon name="graph" size={16} /> 知识图谱
        </button>
        <button type="button" onClick={() => setReviewOpen(true)}>
          <Icon name="history" size={16} /> 到期复习
        </button>
        <button type="button" onClick={() => setActiveFeature('feynman')}>
          <Icon name="mic" size={16} /> 费曼讲一遍
        </button>
      </section>
    </div>
  );
}
