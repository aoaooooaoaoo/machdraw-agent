import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icons';
import { useAppStore } from '../lib/store';
import { ApiError } from '../lib/api';

/**
 * 登录页。
 * 后端 POST /api/auth/login 的行为是"首次输入自动建号"，所以这里不区分注册/登录。
 */
export function LoginGate() {
  const signIn = useAppStore((s) => s.signIn);
  const backendOnline = useAppStore((s) => s.backendOnline);
  const health = useAppStore((s) => s.health);
  const refreshHealth = useAppStore((s) => s.refreshHealth);

  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const accountRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    accountRef.current?.focus();
  }, []);

  async function submit() {
    if (busy) return;
    if (!account.trim()) {
      setError('请输入账号');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn(account, password);
    } catch (err) {
      // 后端错误信息优先：FastAPI 的 detail 已被 ApiError 提取
      setError(err instanceof ApiError ? err.message : (err as Error)?.message || '登录失败');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-backdrop" aria-hidden="true" />
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-mark">
            <Icon name="pencil" size={22} />
          </div>
          <div>
            <div className="login-title">核反应堆物理 AI 助教 Agent</div>
            <div className="login-subtitle">三栏工作台 · 对话 / 证据 / 画布</div>
          </div>
        </div>

        <div className="login-hint">
          <Icon name="spark" size={14} />
          <span>首次输入的账号将自动创建学习账号；密码用于之后找回个人记录。</span>
        </div>

        <form
          className="login-form"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <label className="field">
            <span className="field-label">账号</span>
            <input
              ref={accountRef}
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              placeholder="学号 / 姓名"
              autoComplete="username"
              disabled={busy}
            />
          </label>
          <label className="field">
            <span className="field-label">密码</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="首次留空也可以"
              autoComplete="current-password"
              disabled={busy}
              // 回车提交：input 在 form 内，浏览器默认提交；这里显式兜底一次
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  void submit();
                }
              }}
            />
          </label>

          {error && (
            <div className="form-error" role="alert">
              <Icon name="alert" size={14} />
              <span>{error}</span>
            </div>
          )}

          <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
            {busy ? '正在登录…' : '进入工作台'}
          </button>
        </form>

        <div className={`login-status ${backendOnline === false ? 'is-offline' : ''}`}>
          <span className={`dot ${backendOnline === false ? 'dot-red' : backendOnline ? 'dot-green' : 'dot-gray'}`} />
          {backendOnline === false ? (
            <>
              后端未连接
              <button className="link-btn" type="button" onClick={() => void refreshHealth()}>
                <Icon name="refresh" size={12} /> 重试
              </button>
            </>
          ) : backendOnline ? (
            <>后端已连接 · 模型 {health?.model ?? '—'} · 知识库 {health?.chunks ?? 0} 段</>
          ) : (
            <>正在检测后端…</>
          )}
        </div>
      </div>
    </div>
  );
}
