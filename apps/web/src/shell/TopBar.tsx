import { useEffect, useState } from 'react';
import { useAppStore } from '../lib/store';
import { MOD_KEY } from '../lib/ui';
import { Icon } from './Icons';

const FEEDBACK_KEY = 'rp.feedback';

interface FeedbackRecord {
  account: string;
  text: string;
  at: string;
}

function saveFeedback(record: FeedbackRecord): void {
  try {
    const raw = localStorage.getItem(FEEDBACK_KEY);
    const list: FeedbackRecord[] = raw ? JSON.parse(raw) : [];
    list.push(record);
    localStorage.setItem(FEEDBACK_KEY, JSON.stringify(list.slice(-100)));
  } catch {
    /* 隐私模式忽略 */
  }
}

export function TopBar() {
  const account = useAppStore((s) => s.account);
  const health = useAppStore((s) => s.health);
  const backendOnline = useAppStore((s) => s.backendOnline);
  const signOut = useAppStore((s) => s.signOut);
  const refreshHealth = useAppStore((s) => s.refreshHealth);
  const setPaletteOpen = useAppStore((s) => s.setPaletteOpen);
  const setHistoryOpen = useAppStore((s) => s.setHistoryOpen);
  const setReviewOpen = useAppStore((s) => s.setReviewOpen);
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);

  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (!feedbackOpen) {
      setSent(false);
      setFeedbackText('');
    }
  }, [feedbackOpen]);

  const passwordMode = health?.provider === 'mock' ? '本地抽取式' : health?.provider || '—';

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <div className="brand-mark brand-mark-sm">
          <Icon name="pencil" size={17} />
        </div>
        <div className="brand-text">
          <span className="brand-name">核反应堆物理 AI 助教</span>
          <span className="brand-tag">Agent 工作台</span>
        </div>
      </div>

      <div className="topbar-right">
        <button
          className={`status-chip ${backendOnline === false ? 'is-offline' : backendOnline ? 'is-online' : ''}`}
          type="button"
          onClick={() => void refreshHealth()}
          title="点击重新检测后端连接"
        >
          <span
            className={`dot ${backendOnline === false ? 'dot-red' : backendOnline ? 'dot-green' : 'dot-gray'}`}
          />
          {backendOnline === false ? '后端未连接' : backendOnline ? '已连接' : '检测中'}
        </button>

        <div className="model-chip" title={`provider: ${health?.provider ?? '—'} · ${passwordMode}`}>
          <Icon name="cube" size={14} />
          <span className="model-name">{health?.model ?? '—'}</span>
        </div>

        {account && (
          <div className="account-chip" title={`当前账号：${account}`}>
            <span className="avatar">{account.slice(0, 1).toUpperCase()}</span>
            <span className="account-name">{account}</span>
          </div>
        )}

        <button
          className="icon-btn"
          type="button"
          title={theme === 'dark' ? '切换浅色主题' : '切换深色主题'}
          aria-label="切换主题"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={17} />
        </button>

        <button className="search-btn" type="button" title="历史会话（后端已按天保存）" onClick={() => setHistoryOpen(true)}>
          <Icon name="history" size={15} />
          <span className="search-btn-label">历史</span>
        </button>

        <button className="search-btn" type="button" title="今日复习（按掌握度 + 时间排）" onClick={() => setReviewOpen(true)}>
          <Icon name="target" size={15} />
          <span className="search-btn-label">复习</span>
        </button>

        <button
          className="search-btn"
          type="button"
          title={`搜索模块 / 直接提问 / 操作（${MOD_KEY} + K）`}
          onClick={() => setPaletteOpen(true)}
        >
          <Icon name="search" size={15} />
          <span className="search-btn-label">搜索</span>
          <kbd className="topbar-kbd">{MOD_KEY} K</kbd>
        </button>

        <button className="btn btn-ghost" type="button" onClick={() => setFeedbackOpen(true)}>
          <Icon name="feedback" size={16} />
          <span>意见反馈</span>
        </button>

        <button className="icon-btn" type="button" title="退出登录" onClick={signOut}>
          <Icon name="logout" size={17} />
        </button>
      </div>

      {feedbackOpen && (
        <div className="modal-mask" role="dialog" aria-modal="true" aria-label="意见反馈">
          <div className="modal">
            <div className="modal-head">
              <h3>意见反馈</h3>
              <button className="icon-btn" type="button" onClick={() => setFeedbackOpen(false)}>
                <Icon name="x" size={17} />
              </button>
            </div>
            {sent ? (
              <div className="modal-body">
                <p className="modal-note">
                  <Icon name="check" size={15} /> 已记录到本地浏览器（后端暂未提供反馈接口，提交后请直接告知助教）。
                </p>
                <button className="btn btn-primary" type="button" onClick={() => setFeedbackOpen(false)}>
                  知道了
                </button>
              </div>
            ) : (
              <div className="modal-body">
                <textarea
                  className="modal-textarea"
                  rows={5}
                  placeholder="比如：证据卡看不出教材章节 / 临界计算结果对不上 / 某个模块答非所问…"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                />
                <div className="modal-actions">
                  <button className="btn btn-ghost" type="button" onClick={() => setFeedbackOpen(false)}>
                    取消
                  </button>
                  <button
                    className="btn btn-primary"
                    type="button"
                    disabled={!feedbackText.trim()}
                    onClick={() => {
                      saveFeedback({
                        account: account ?? 'anonymous',
                        text: feedbackText.trim(),
                        at: new Date().toISOString(),
                      });
                      setSent(true);
                    }}
                  >
                    提交
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
