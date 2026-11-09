/**
 * 学习者数据本地镜像：Render 免费档重启会清空 SQLite，
 * 这里把掌握度同时写进浏览器 localStorage；下次登录先做一次 import。
 */
import { getMastery, importMastery, type MasteryItem } from './api';

const KEY = 'rp.mastery.v1';

function cacheKey(account: string): string {
  return `${KEY}:${account}`;
}

export function readLocalMastery(account: string | null): Record<string, MasteryItem> {
  if (!account) return {};
  try {
    const raw = localStorage.getItem(cacheKey(account));
    const data = raw ? JSON.parse(raw) : {};
    return data && typeof data === 'object' ? (data as Record<string, MasteryItem>) : {};
  } catch {
    return {};
  }
}

export function writeLocalMastery(account: string | null, mastery: Record<string, MasteryItem>): void {
  if (!account) return;
  try {
    localStorage.setItem(cacheKey(account), JSON.stringify(mastery || {}));
  } catch {
    /* 配额/隐私模式忽略 */
  }
}

/** 登录后：先把本地镜像推给服务端，再以服务端结果为准回写本地。 */
export async function syncMastery(account: string): Promise<void> {
  const local = readLocalMastery(account);
  try {
    if (Object.keys(local).length > 0) {
      const res = await importMastery(local, account);
      writeLocalMastery(account, res.mastery || {});
    } else {
      const res = await getMastery(account);
      writeLocalMastery(account, res.mastery || {});
    }
  } catch {
    /* 同步失败不影响使用，下次再试 */
  }
}

/** 判分/自评后：拉一次服务端掌握度写入本地镜像。 */
export async function refreshMasteryCache(account: string | null): Promise<void> {
  if (!account) return;
  try {
    const res = await getMastery(account);
    writeLocalMastery(account, res.mastery || {});
  } catch {
    /* ignore */
  }
}
