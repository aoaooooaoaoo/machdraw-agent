import { useEffect, useMemo, useState } from 'react';
import { useActiveSession, useAppStore } from '../lib/store';
import {
  getCanvasDef,
  getPreview,
  getPreviewType,
  isPlaceholder,
  KNOWN_CANVAS_TYPES,
  shouldAutoOpen,
} from '../modules/registry';
import type { CanvasPreview } from '../lib/canvasFeature';
import type { ArtifactState } from '../lib/types';
import { Icon } from './Icons';

/**
 * 右栏：画布。
 * - 一次问答可能推送多个 artifact（如 graph + evidence），用标签页按 artifactType 切换渲染器；
 * - 不认识的 artifactType 由 registry 回落到占位渲染器，不抛错；
 * - 没有 artifact 时显示空态；示例数据由 features/<id>/index.ts 的 preview 声明；
 * - 画布可收起：产出 artifact 时，仅 autoOpenCanvas=true 的展示型画布自动展开。
 */
export function CanvasPanel() {
  const session = useActiveSession();
  const activeFeature = useAppStore((s) => s.activeFeature);
  const modules = useAppStore((s) => s.modules);
  const setDraft = useAppStore((s) => s.setDraft);

  const [demoType, setDemoType] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [selected, setSelected] = useState(0);

  const artifacts = session.artifacts;
  const activeModule = modules.find((m) => m.id === activeFeature);

  // 新一轮 artifact 到达 / 切换模块 → 默认看最后一个
  useEffect(() => {
    setSelected(artifacts.length > 0 ? artifacts.length - 1 : 0);
  }, [artifacts.length, activeFeature]);

  // 切模块：收起示例；按该模块声明的画布类型决定初始开合
  useEffect(() => {
    setDemoType(null);
    const kinds = activeModule?.canvas_kinds ?? [];
    if (kinds.length === 0) {
      // 全局对话没有模块级 autoOpen 声明：回到默认展开
      setCollapsed(false);
      return;
    }
    setCollapsed(!kinds.some((type) => shouldAutoOpen(type)));
  }, [activeFeature, activeModule]);

  // artifact 到达：只有 autoOpenCanvas=true 的类型才把画布重新展开；
  // false 的类型保持用户当前状态（用户可能正收着画布看正文）。
  const latestArtifactType = artifacts.length > 0 ? artifacts[artifacts.length - 1].artifactType : null;
  useEffect(() => {
    if (latestArtifactType && shouldAutoOpen(latestArtifactType)) setCollapsed(false);
  }, [latestArtifactType, artifacts.length]);

  // 收起状态把右栏从 --right-w 压成 48px 细条；恢复时清掉内联变量。
  // 窄屏（<=820px）画布在底部整行，不参与侧边收起。
  useEffect(() => {
    const workbench = document.querySelector<HTMLElement>('.workbench');
    if (!workbench) return;
    const mq = window.matchMedia('(max-width: 820px)');
    const apply = () => {
      if (collapsed && !mq.matches) workbench.style.setProperty('--right-w', '48px');
      else workbench.style.removeProperty('--right-w');
    };
    apply();
    mq.addEventListener('change', apply);
    return () => {
      mq.removeEventListener('change', apply);
      workbench.style.removeProperty('--right-w');
    };
  }, [collapsed]);

  // 示例数据来自 registry（features/*/index.ts 的 preview），壳不再 import 任何 demo.ts
  const previews = useMemo(() => {
    const kinds = activeModule?.canvas_kinds ?? [];
    const seen = new Set<string>();
    const list: { type: string; preview: CanvasPreview }[] = [];
    for (const type of kinds) {
      if (seen.has(type)) continue;
      seen.add(type);
      const preview = getPreview(type);
      if (preview) list.push({ type, preview });
    }
    return list;
  }, [activeModule]);

  const realArtifact = artifacts[Math.min(selected, Math.max(0, artifacts.length - 1))];
  const demoArtifact = useMemo<ArtifactState | null>(() => {
    if (!demoType) return null;
    const hit = previews.find((p) => p.type === demoType);
    if (!hit) return null;
    const artifactType = getPreviewType(hit.type) ?? hit.type;
    return {
      artifactType,
      data: { ...hit.preview.data },
      receivedAt: Date.now(),
    };
  }, [demoType, previews]);

  // 知识图谱模块没有 chat artifact 时，也直接渲染画布（全览星图入口），而不是空态
  const entryArtifact = useMemo<ArtifactState | null>(() => {
    if (activeFeature !== 'graph' || realArtifact) return null;
    return { artifactType: 'graph', data: {}, receivedAt: Date.now() };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeFeature, realArtifact]);

  const shown = realArtifact ?? demoArtifact ?? entryArtifact;
  const isDemo = !realArtifact && Boolean(demoArtifact);
  const isEntry = !realArtifact && !demoArtifact && Boolean(entryArtifact);

  // 没有 artifact 时，用模块声明的第一个 canvas_kind 作为"当前画布"标题
  const fallbackType = activeModule?.canvas_kinds?.[0] ?? 'evidence';
  const shownType = shown?.artifactType ?? fallbackType;
  const def = getCanvasDef(shownType);
  const CanvasComponent = def.component;

  const placeholders = KNOWN_CANVAS_TYPES.filter(isPlaceholder);
  const onAsk = (text: string) => setDraft(text);

  const tabs = useMemo(
    () =>
      artifacts.map((a) => ({
        type: a.artifactType,
        title: getCanvasDef(a.artifactType).title,
        receivedAt: a.receivedAt,
      })),
    [artifacts],
  );

  // 收起态：只剩一条可点击的细栏，用户随时能手动展开（内容不丢，只是不抢屏）
  if (collapsed) {
    return (
      <aside
        className="canvas canvas-collapsed"
        aria-label="画布已收起"
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: '10px 0' }}
      >
        <button
          className="icon-btn"
          type="button"
          title="展开画布"
          aria-label="展开画布"
          onClick={() => setCollapsed(false)}
        >
          <Icon name="expand" size={16} />
        </button>
        <span style={{ writingMode: 'vertical-rl', fontSize: 10.5, color: 'var(--text-3)', letterSpacing: '0.18em' }}>
          画布
        </span>
        <span style={{ writingMode: 'vertical-rl', fontSize: 9, color: 'var(--text-3)' }}>已收起</span>
      </aside>
    );
  }

  return (
    <aside className="canvas">
      <div className="canvas-head">
        <div className="canvas-title-wrap">
          <div className="canvas-kicker">画布</div>
          <h2 className="canvas-title">{def.title}</h2>
        </div>
        <div className="canvas-tags">
          {isDemo && <span className="chip chip-demo">示例数据</span>}
          {isEntry && <span className="chip chip-entry">全览入口</span>}
          <span className="chip chip-type mono">{shownType}</span>
          <button
            className="icon-btn"
            type="button"
            title="收起画布"
            aria-label="收起画布"
            onClick={() => setCollapsed(true)}
          >
            <Icon name="chevron" size={14} style={{ transform: 'rotate(90deg)' }} />
          </button>
        </div>
      </div>
      <p className="canvas-hint">{def.hint}</p>

      {/* 示例查看中：允许直接切换到同类其它示例（不用回空态） */}
      {isDemo && previews.length > 1 && (
        <div className="canvas-demo-switch">
          <span className="canvas-demo-switch-label">示例</span>
          {previews.map(({ type, preview }) => (
            <button
              key={type}
              type="button"
              className={`canvas-demo-chip ${demoType === type ? 'is-active' : ''}`}
              onClick={() => setDemoType(type)}
            >
              {preview.label}
            </button>
          ))}
        </div>
      )}

      {tabs.length > 1 && (
        <div className="canvas-tabs" role="tablist" aria-label="本轮画布">
          {tabs.map((t, i) => (
            <button
              key={`${t.type}_${t.receivedAt}_${i}`}
              type="button"
              role="tab"
              aria-selected={i === selected}
              className={`canvas-tab ${i === selected ? 'is-active' : ''}`}
              onClick={() => setSelected(i)}
              title={t.title}
            >
              <span className="canvas-tab-type mono">{t.type}</span>
            </button>
          ))}
        </div>
      )}

      <div className="canvas-content">
        {shown ? (
          <CanvasComponent artifact={shown} onAsk={onAsk} demo={isDemo} />
        ) : (
          <div className="canvas-empty">
            <div className="empty-mark">
              <Icon name={activeModule?.icon ?? 'layers'} size={24} />
            </div>
            <h3>还没有画布内容</h3>
            <p>
              在中间提问后，
              <strong>{activeModule?.name ?? '当前模块'}</strong>
              会把检索/计算结果推到这里。
            </p>

            <div className="canvas-kinds">
              <span className="canvas-kinds-label">该模块声明的 artifactType</span>
              <div className="canvas-kinds-list">
                {(activeModule?.canvas_kinds ?? [fallbackType]).map((k) => (
                  <span className="chip" key={k}>
                    {k}
                  </span>
                ))}
              </div>
            </div>

            {previews.length > 0 && (
              <div className="canvas-demos">
                {previews.map(({ type, preview }) => (
                  <button
                    key={type}
                    className="btn btn-ghost btn-demo"
                    type="button"
                    onClick={() => setDemoType(type)}
                  >
                    <Icon name="spark" size={14} />
                    {preview.label}
                  </button>
                ))}
              </div>
            )}

            <p className="canvas-tip">
              已实现渲染器：{KNOWN_CANVAS_TYPES.length - placeholders.length} / {KNOWN_CANVAS_TYPES.length}
              {placeholders.length === 0
                ? '；全部 artifactType 都有专用渲染器，未知类型仍回落占位。'
                : `；其余 ${placeholders.length} 种（${placeholders.join(' / ')}）走统一占位渲染器。`}
            </p>
          </div>
        )}
      </div>

      <div className="canvas-foot">
        {shown ? (
          isEntry ? (
            <>
              <span className="mono">graph</span>
              <span className="sep">·</span>
              <span>入口：左侧模块导航 · 全课程星图</span>
              <span className="sep">·</span>
              <span>点节点进入焦点关系</span>
            </>
          ) : (
            <>
              <span className="mono">{shown.artifactType}</span>
              <span className="sep">·</span>
              <span>接收于 {new Date(shown.receivedAt).toLocaleTimeString('zh-CN', { hour12: false })}</span>
              {isDemo && (
                <>
                  <span className="sep">·</span>
                  <span>本地示例（后端数据未到）</span>
                </>
              )}
              {artifacts.length > 1 && (
                <>
                  <span className="sep">·</span>
                  <span>本轮 {artifacts.length} 个画布</span>
                </>
              )}
            </>
          )
        ) : (
          <>
            <span>等待 artifact…</span>
            <span className="sep">·</span>
            <span>POST /api/chat 的 SSE 事件流自动推送</span>
          </>
        )}
      </div>
    </aside>
  );
}
