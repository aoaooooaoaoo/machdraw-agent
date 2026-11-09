/**
 * 学习数据备份/恢复：
 *  - 导出：服务端 master/wrongbook/records + 浏览器里的 sessions/mastery 镜像 → 一个 JSON 文件；
 *  - 导入：先 POST /api/restore（只增不减），再把本地 sessions/mastery 写回 localStorage。
 * 适合换设备/换浏览器，或 Render 重启前手动留档。
 */
import { getBackup, restoreBackup } from './api';
import { readLocalMastery, writeLocalMastery } from './learner';

const SESSION_PREFIX = 'rp.sessions.v1:';
const MASTERY_PREFIX = 'rp.mastery.v1:';

function readLocal<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export async function exportLearningData(account: string): Promise<void> {
  const server = await getBackup(account);
  const sessions = readLocal<Record<string, unknown>>(`${SESSION_PREFIX}${account}`);
  const mastery = readLocal<Record<string, unknown>>(`${MASTERY_PREFIX}${account}`);
  const bundle = {
    format: 'reactor-physics-learning-backup',
    version: 1,
    account,
    exported_at: new Date().toISOString(),
    server,
    sessions: sessions || {},
    mastery_local: mastery || {},
  };
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `reactor-physics-backup-${account}-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function importLearningData(
  file: File,
  account: string,
): Promise<{ importedMastery: number; importedWrongbook: number }> {
  const text = await file.text();
  const bundle = JSON.parse(text) as Record<string, unknown>;
  const server = (bundle.server || {}) as {
    mastery?: Record<string, unknown>;
    wrongbook?: unknown[];
    records?: Record<string, unknown>;
  };
  const res = await restoreBackup(
    {
      mastery: server.mastery || bundle.mastery_local || {},
      wrongbook: server.wrongbook || [],
      records: server.records || {},
    },
    account,
  );
  if (bundle.mastery_local && typeof bundle.mastery_local === 'object') {
    writeLocalMastery(
      account,
      bundle.mastery_local as Parameters<typeof writeLocalMastery>[1],
    );
  } else {
    const local = readLocalMastery(account);
    writeLocalMastery(account, local);
  }
  if (bundle.sessions && typeof bundle.sessions === 'object') {
    try {
      localStorage.setItem(`${SESSION_PREFIX}${account}`, JSON.stringify(bundle.sessions));
    } catch {
      /* ignore */
    }
  }
  return {
    importedMastery: res.imported_mastery || 0,
    importedWrongbook: res.imported_wrongbook || 0,
  };
}
