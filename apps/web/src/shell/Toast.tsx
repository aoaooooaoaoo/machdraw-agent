import { useEffect, useState } from 'react';
import { subscribeToasts, type ToastItem } from '../lib/ui';
import { Icon } from './Icons';

/** 全局 toast 视口：右下角浮出，2.6s 自动消失。 */
export function ToastViewport() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => subscribeToasts(setItems), []);

  if (items.length === 0) return null;
  return (
    <div className="toast-viewport" role="status" aria-live="polite">
      {items.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          <Icon name={t.kind === 'error' ? 'alert' : t.kind === 'info' ? 'spark' : 'check'} size={14} />
          <span>{t.text}</span>
        </div>
      ))}
    </div>
  );
}
