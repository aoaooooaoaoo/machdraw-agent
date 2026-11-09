import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react';
import type { GraphFull, GraphNodeInfo } from '../../lib/types';
import { Icon } from '../../shell/Icons';
import { REL_STYLE, TIER_CN, stateColor, tierOf } from './constants';
import { LAYOUT_H, LAYOUT_W, buildGraphLayout, estimateLabelWidth, type Cluster, type LayoutNode } from './layout';

interface ViewState {
  x: number;
  y: number;
  k: number;
}

interface HoverCard {
  node: GraphNodeInfo;
  left: number;
  top: number;
  below: boolean;
}

interface OverviewProps {
  full: GraphFull | null;
  fullError: string | null;
  focusId?: string;
  onFocus: (id: string) => void;
  externalSelectedId?: string | null;
  onSelect?: (id: string | null) => void;
  hiddenLevels?: Set<string>;
  hiddenSectors?: Set<number>;
  denseLabels?: boolean;
  fillHeight?: boolean;
}

function shortPill(text: string): string {
  return text.length > 12 ? `${text.slice(0, 12)}…` : text;
}

/**
 * 全览图谱（重绘版）：按章分簇的有机网络。
 *
 * 视觉：章节彩色晕圈 + 节点按章着色 + 只显示高优先级标签（core / 高连接 / 悬停 / 放大后），
 * 关系线默认很淡、悬停时高亮一跳邻居。交互与旧版一致：滚轮缩放、拖拽平移、
 * 搜索定位、筛选、悬停卡片、点节点进入焦点关系。
 */
export function Overview({
  full,
  fullError,
  focusId,
  onFocus,
  externalSelectedId,
  onSelect,
  hiddenLevels,
  hiddenSectors,
  denseLabels,
  fillHeight,
}: OverviewProps) {
  const layout = useMemo(() => (full ? buildGraphLayout(full) : null), [full]);

  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const viewRef = useRef<ViewState>({ x: 0, y: 0, k: 1 });
  const zoomBadgeRef = useRef<HTMLSpanElement>(null);
  const dragRef = useRef<{ sx: number; sy: number; ox: number; oy: number; moved: boolean } | null>(null);
  const lastDragAtRef = useRef(0);

  const [dragging, setDragging] = useState(false);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [hoverCard, setHoverCard] = useState<HoverCard | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const [showAllLabels, setShowAllLabels] = useState(false);
  const [query, setQuery] = useState('');
  const [searchMsg, setSearchMsg] = useState<string | null>(null);
  const [searchOk, setSearchOk] = useState(true);

  useEffect(() => {
    if (externalSelectedId !== undefined) setSelectedId(externalSelectedId);
  }, [externalSelectedId]);

  function selectNode(id: string | null) {
    setSelectedId(id);
    onSelect?.(id);
  }

  function applyView(next: ViewState) {
    const prev = viewRef.current;
    viewRef.current = next;
    if (gRef.current) {
      gRef.current.setAttribute('transform', `translate(${next.x} ${next.y}) scale(${next.k})`);
    }
    if (zoomBadgeRef.current) zoomBadgeRef.current.textContent = `${Math.round(next.k * 100)}%`;
    if (prev.k < 1.5 !== next.k < 1.5) setShowAllLabels(next.k >= 1.5);
  }

  /** 初始把整张图缩放到"刚好铺满"可视区（避免四周大片空白）。 */
  function fitView() {
    if (!layout) return;
    const bw = Math.max(1, layout.bounds.maxX - layout.bounds.minX);
    const bh = Math.max(1, layout.bounds.maxY - layout.bounds.minY);
    const pad = 70;
    const k = Math.min(1.35, (LAYOUT_W - pad * 2) / bw, (LAYOUT_H - pad * 2) / bh);
    const cx = (layout.bounds.minX + layout.bounds.maxX) / 2;
    const cy = (layout.bounds.minY + layout.bounds.maxY) / 2;
    applyView({ k, x: LAYOUT_W / 2 - cx * k, y: LAYOUT_H / 2 - cy * k });
  }

  useEffect(() => {
    fitView();
    selectNode(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout]);

  // 滚轮缩放：以光标位置为中心
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const px = ((e.clientX - rect.left) / rect.width) * LAYOUT_W;
      const py = ((e.clientY - rect.top) / rect.height) * LAYOUT_H;
      const v = viewRef.current;
      const k = Math.min(6, Math.max(0.35, v.k * Math.exp(-e.deltaY * 0.0015)));
      const ratio = k / v.k;
      applyView({ k, x: px - (px - v.x) * ratio, y: py - (py - v.y) * ratio });
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout]);

  function zoomBy(factor: number) {
    const v = viewRef.current;
    const k = Math.min(6, Math.max(0.35, v.k * factor));
    const ratio = k / v.k;
    applyView({
      k,
      x: LAYOUT_W / 2 - (LAYOUT_W / 2 - v.x) * ratio,
      y: LAYOUT_H / 2 - (LAYOUT_H / 2 - v.y) * ratio,
    });
  }

  function centerOn(placed: LayoutNode, k = 2.2) {
    applyView({ k, x: LAYOUT_W / 2 - placed.x * k, y: LAYOUT_H / 2 - placed.y * k });
    selectNode(placed.node.id);
  }

  function resetView() {
    fitView();
    selectNode(null);
    setSearchMsg(null);
  }

  function doSearch(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q || !layout) return;
    const low = q.toLowerCase();
    const found = layout.nodes.find(
      (p) => p.node.label.toLowerCase().includes(low) || (p.node.kp_id ?? '').toLowerCase().includes(low),
    );
    if (found) {
      centerOn(found);
      setSearchMsg(`已定位：${found.node.label}（${TIER_CN[tierOf(found.node)] ?? found.node.tier}）`);
      setSearchOk(true);
    } else {
      setSearchMsg(`未找到「${q}」，换个名字或 kp_id 试试`);
      setSearchOk(false);
    }
  }

  function onPointerDown(e: ReactPointerEvent<SVGSVGElement>) {
    if (e.button !== 0) return;
    const v = viewRef.current;
    dragRef.current = { sx: e.clientX, sy: e.clientY, ox: v.x, oy: v.y, moved: false };
    try {
      (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    } catch {
      /* 合成事件没有真实 pointer，忽略 */
    }
    setDragging(true);
  }

  function onPointerMove(e: ReactPointerEvent<SVGSVGElement>) {
    const d = dragRef.current;
    const el = svgRef.current;
    if (!d || !el) return;
    const rect = el.getBoundingClientRect();
    if (Math.hypot(e.clientX - d.sx, e.clientY - d.sy) > 3) d.moved = true;
    const dx = ((e.clientX - d.sx) / rect.width) * LAYOUT_W;
    const dy = ((e.clientY - d.sy) / rect.height) * LAYOUT_H;
    applyView({ k: viewRef.current.k, x: d.ox + dx, y: d.oy + dy });
  }

  function endDrag() {
    const d = dragRef.current;
    if (d?.moved) lastDragAtRef.current = Date.now();
    dragRef.current = null;
    setDragging(false);
    setHoverCard(null);
  }

  function handleNodeEnter(p: LayoutNode) {
    setHoverId(p.node.id);
    const v = viewRef.current;
    const left = Math.max(16, Math.min(84, ((v.x + p.x * v.k) / LAYOUT_W) * 100));
    const topRaw = ((v.y + p.y * v.k) / LAYOUT_H) * 100;
    const top = Math.max(6, Math.min(94, topRaw));
    setHoverCard({ node: p.node, left, top, below: topRaw < 42 });
  }

  function handleNodeLeave() {
    setHoverId(null);
    setHoverCard(null);
  }

  function handleNodeClick(id: string) {
    if (Date.now() - lastDragAtRef.current < 350) return;
    if (onSelect) {
      if (selectedId === id) resetView();
      else selectNode(id);
      return;
    }
    onFocus(id);
  }

  const hoverSet = useMemo(() => {
    if (!hoverId || !layout) return null;
    const set = new Set<string>([hoverId]);
    layout.adjacency.get(hoverId)?.forEach((id) => set.add(id));
    return set;
  }, [hoverId, layout]);

  const visibleNodes = useMemo(() => {
    if (!layout) return [];
    return layout.nodes.filter(
      (p) => !hiddenLevels?.has(tierOf(p.node)) && !hiddenSectors?.has(p.node.sector ?? -1),
    );
  }, [layout, hiddenLevels, hiddenSectors]);

  const visibleIds = useMemo(() => new Set(visibleNodes.map((p) => p.node.id)), [visibleNodes]);

  /** 标签排布：按优先级尝试放置，互相重叠的直接放弃（防止"标签汤"）。 */
  /** 章名 pill 摆放：上/下/左/右四个候选位，选不与任何节点圆重叠的位置。 */
  const clusterLabels = useMemo(() => {
    if (!layout) return [] as { c: Cluster; label: string; w: number; x: number; y: number }[];
    return layout.clusters.map((c) => {
      const label = `${c.short} · ${c.count}`;
      const w = Math.max(estimateLabelWidth(label) + 26, 78);
      const h = 23;
      // 固定放在簇椭圆正上方，只做画布内水平夹紧；不做上下左右跳位（避免标签"漂"到别的簇旁）
      const x = Math.max(10, Math.min(LAYOUT_W - w - 10, c.cx - c.rx + 2));
      const y = Math.max(8, c.cy - c.ry - 30);
      return { c, label, w, x, y };
    });
  }, [layout]);
  const labelBoxes = useMemo(() => {
    if (!layout) return [] as { p: LayoutNode; w: number; x: number; y: number; anchor: 'start' | 'end' }[];
    const candidates = visibleNodes
      .filter((p) => {
        const t = tierOf(p.node);
        const selected = selectedId === p.node.id || focusId === p.node.id;
        if (selected || hoverId === p.node.id) return true;
        if (t === 'core') return true;
        if (showAllLabels) return true;
        if (p.degree >= 5) return true;
        return false;
      })
      .sort((a, b) => {
        const ta = tierOf(a.node) === 'core' ? 2 : a.degree >= 6 ? 1 : 0;
        const tb = tierOf(b.node) === 'core' ? 2 : b.degree >= 6 ? 1 : 0;
        return tb - ta || b.degree - a.degree;
      });
    const accepted: { p: LayoutNode; w: number; x: number; y: number; anchor: 'start' | 'end' }[] = [];
    const boxes: { x0: number; y0: number; x1: number; y1: number }[] = [];
    for (const p of candidates) {
      const text = shortPill(p.node.label);
      const w = estimateLabelWidth(text) + 6;
      const preferRight = p.x < LAYOUT_W - 150;
      const x = preferRight ? p.x + p.r + 4 : p.x - p.r - 4 - w;
      const y = p.y - 7;
      const box = { x0: x - 2, y0: y - 3, x1: x + w, y1: y + 15 };
      const hit = boxes.some((b) => !(box.x1 < b.x0 || box.x0 > b.x1 || box.y1 < b.y0 || box.y0 > b.y1));
      if (hit) continue;
      boxes.push(box);
      accepted.push({ p, w, x, y, anchor: preferRight ? 'start' : 'end' });
    }
    return accepted;
  }, [layout, visibleNodes, selectedId, focusId, hoverId, showAllLabels]);
  void denseLabels;

  if (!full || !layout) {
    return (
      <div className="kg-star-state">
        {fullError ? (
          <>
            <Icon name="alert" size={16} />
            <p>图谱数据加载失败：{fullError}</p>
          </>
        ) : (
          <>
            <span className="spinner" /> 正在加载全课程图谱…
          </>
        )}
      </div>
    );
  }

  const chapterOfSector = new Map<number, string>();
  for (const c of layout.clusters) {
    const node = full.nodes.find((n) => (n.chapter || '未分章') === c.chapter);
    if (node && typeof node.sector === 'number') chapterOfSector.set(node.sector, c.chapter);
  }
  void chapterOfSector;

  return (
    <>
      <div className="kg-overview-toolbar">
        <form className="kg-search" onSubmit={doSearch}>
          <Icon name="search" size={13} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索知识点 / kp_id…"
            aria-label="搜索知识点"
          />
          <button type="submit" className="btn btn-ghost btn-xs">
            定位
          </button>
        </form>
        <div className="kg-zoom-controls">
          <button type="button" title="放大" onClick={() => zoomBy(1.25)}>
            ＋
          </button>
          <button type="button" title="缩小" onClick={() => zoomBy(0.8)}>
            －
          </button>
          <button type="button" title="适应画布" onClick={resetView}>
            适应
          </button>
          <button
            type="button"
            title="切换浅色 / 星图主题"
            className={theme === 'dark' ? 'is-on' : ''}
            onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
          >
            {theme === 'dark' ? '浅色' : '星图'}
          </button>
        </div>
      </div>

      {searchMsg && <div className={`kg-search-msg ${searchOk ? 'is-ok' : 'is-warn'}`}>{searchMsg}</div>}

      <div className={`kg-star-wrap ${theme === 'dark' ? 'is-dark' : ''}`} style={fillHeight ? { flex: 1, minHeight: 0 } : undefined}>
        <svg
          ref={svgRef}
          className={`kg-star-svg ${dragging ? 'is-dragging' : ''}`}
          viewBox={`0 0 ${LAYOUT_W} ${LAYOUT_H}`}
          role="img"
          aria-label="全课程知识图谱"
          preserveAspectRatio="xMidYMid meet"
          style={fillHeight ? { width: '100%', height: '100%' } : undefined}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
        >
          <defs>
            <radialGradient id="kgBg" cx="50%" cy="42%" r="78%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="62%" stopColor="#f7fafe" />
              <stop offset="100%" stopColor="#edf3fb" />
            </radialGradient>
            <radialGradient id="kgBgDark" cx="50%" cy="40%" r="82%">
              <stop offset="0%" stopColor="#0d1728" />
              <stop offset="62%" stopColor="#0b1220" />
              <stop offset="100%" stopColor="#070d18" />
            </radialGradient>
            <pattern id="kgDots" width="26" height="26" patternUnits="userSpaceOnUse">
              <circle cx="1.2" cy="1.2" r="0.9" fill="#dbe4f0" />
            </pattern>
            <pattern id="kgDotsDark" width="26" height="26" patternUnits="userSpaceOnUse">
              <circle cx="1.2" cy="1.2" r="0.9" fill="#24344d" />
            </pattern>
            <filter id="kgSoftBlur" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="14" />
            </filter>
          </defs>

          <rect
            x="0"
            y="0"
            width={LAYOUT_W}
            height={LAYOUT_H}
            fill={theme === 'dark' ? 'url(#kgBgDark)' : 'url(#kgBg)'}
            onClick={() => {
              if (Date.now() - lastDragAtRef.current < 350) return;
              if (onSelect) resetView();
            }}
          />
          <rect
            x="0"
            y="0"
            width={LAYOUT_W}
            height={LAYOUT_H}
            fill={theme === 'dark' ? 'url(#kgDotsDark)' : 'url(#kgDots)'}
            opacity="0.55"
          />

          <g ref={gRef} transform="translate(0 0) scale(1)">
            {/* 章节晕圈：先画模糊底色，再画虚线轮廓 */}
            <g className="kg-cluster-layer">
              {layout.clusters.map((c) => {
                const node = full.nodes.find((n) => (n.chapter || '未分章') === c.chapter);
                if (hiddenSectors?.has(node?.sector ?? -1)) return null;
                return (
                  <g key={`blob-${c.chapter}`} transform={`rotate(${(c.angle * 180) / Math.PI} ${c.cx} ${c.cy})`}>
                    <ellipse
                      cx={c.cx}
                      cy={c.cy}
                      rx={c.rx + 14}
                      ry={c.ry + 14}
                      fill={c.color}
                      opacity={theme === 'dark' ? 0.2 : 0.075}
                      filter="url(#kgSoftBlur)"
                    />
                    <ellipse
                      cx={c.cx}
                      cy={c.cy}
                      rx={c.rx}
                      ry={c.ry}
                      fill="none"
                      stroke={c.color}
                      strokeOpacity={theme === 'dark' ? 0.42 : 0.22}
                      strokeDasharray="5 7"
                    />
                  </g>
                );
              })}
            </g>

            {/* 关系边 */}
            <g className="kg-edge-layer">
              {layout.edges.map((e, i) => {
                if (!visibleIds.has(e.source) || !visibleIds.has(e.target)) return null;
                const style = REL_STYLE[e.rel] ?? REL_STYLE.prereq;
                const active = Boolean(hoverId) && (e.source === hoverId || e.target === hoverId);
                const dim = Boolean(hoverId) && !active;
                const same = layout.nodeMap.get(e.source)!.chapter === layout.nodeMap.get(e.target)!.chapter;
                return (
                  <path
                    key={`e-${i}`}
                    d={e.d}
                    fill="none"
                    stroke={style.stroke}
                    strokeWidth={active ? 2 : 1.05}
                    strokeDasharray={style.dash}
                    strokeOpacity={dim ? 0.03 : active ? 0.9 : same ? 0.34 : 0.13}
                    strokeLinecap="round" vectorEffect="non-scaling-stroke"
                  />
                );
              })}
            </g>

            {/* 节点 */}
            <g className="kg-node-layer">
              {visibleNodes.map((p) => {
                const isHover = hoverId === p.node.id;
                const isSelected = selectedId === p.node.id || focusId === p.node.id;
                const dim = hoverSet ? !hoverSet.has(p.node.id) : false;
                const core = tierOf(p.node) === 'core';
                return (
                  <g
                    key={p.node.id}
                    className={`kg-gnode ${dim ? 'is-dim' : ''} ${isHover ? 'is-hover' : ''} ${
                      isSelected ? 'is-selected' : ''
                    }`}
                    onMouseEnter={() => handleNodeEnter(p)}
                    onMouseLeave={handleNodeLeave}
                    onClick={() => handleNodeClick(p.node.id)}
                    role="button"
                    aria-label={`${p.node.label}（${TIER_CN[tierOf(p.node)] ?? p.node.tier}）`}
                  >
                    <title>{`${p.node.label}\n${p.node.kp_id ?? ''}\n${p.node.chapter ?? ''}`}</title>
                    <circle cx={p.x} cy={p.y} r={p.r + 6} fill={p.color} opacity={isHover ? 0.28 : core ? 0.18 : 0.1} />
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={p.r}
                      fill={p.color}
                      stroke={theme === 'dark' ? '#0b1220' : '#ffffff'}
                      strokeWidth={core ? 2.4 : 1.6}
                    />
                    {core && (
                      <circle cx={p.x} cy={p.y} r={p.r + 3.2} fill="none" stroke={p.color} strokeOpacity="0.35" strokeWidth="1" />
                    )}
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={Math.max(2, p.r - 3.2)}
                      fill={theme === 'dark' ? '#0b1220' : '#ffffff'}
                      opacity={isSelected || isHover ? 0.55 : 0.28}
                    />
                    {isHover && <circle cx={p.x} cy={p.y} r={p.r + 10} fill="none" stroke={p.color} strokeOpacity="0.5" />}
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={1.9}
                      fill={stateColor(p.node.state)}
                      stroke={theme === 'dark' ? '#0b1220' : '#fff'}
                      strokeWidth="0.8"
                    />
                  </g>
                );
              })}
            </g>

            {/* 标签层（防重叠） */}
            <g className="kg-label-layer">
              {labelBoxes.map(({ p, x, y, anchor }) => (
                <text
                  key={`l-${p.node.id}`}
                  x={x}
                  y={y}
                  textAnchor={anchor}
                  className={`kg-glabel ${
                    selectedId === p.node.id || focusId === p.node.id || hoverId === p.node.id ? 'is-strong' : ''
                  }`}
                  style={{ paintOrder: 'stroke', stroke: theme === 'dark' ? 'rgba(7,13,24,0.92)' : 'rgba(255,255,255,0.92)', strokeWidth: 3.2 }}
                >
                  {shortPill(p.node.label)}
                </text>
              ))}
            </g>

            {/* 章名标签（始终在最上层） */}
                        <g className="kg-cluster-label-layer">
              {clusterLabels.map(({ c, label, w, x, y }) => {
                const node = full.nodes.find((n) => (n.chapter || '未分章') === c.chapter);
                if (hiddenSectors?.has(node?.sector ?? -1)) return null;
                return (
                  <g
                    key={`cl-${c.chapter}`}
                    className="kg-clabel"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      applyView({ k: 1.7, x: LAYOUT_W / 2 - c.cx * 1.7, y: LAYOUT_H / 2 - c.cy * 1.7 });
                    }}
                  >
                    <rect x={x} y={y} rx="11" ry="11" width={w} height="23" fill={theme === 'dark' ? 'rgba(11,18,32,0.94)' : '#ffffff'} stroke={c.color} strokeOpacity={theme === 'dark' ? '0.75' : '0.5'} />
                    <text x={x + w / 2} y={y + 15.5} textAnchor="middle" fill={c.color} className="kg-clabel-text">
                      {label}
                    </text>
                  </g>
                );
              })}
            </g>
          </g>
        </svg>

        <span className="kg-zoom-badge" ref={zoomBadgeRef}>
          100%
        </span>

        {hoverCard && (
          <div
            className="kg-hover-card"
            style={{
              left: `${hoverCard.left}%`,
              top: `${hoverCard.top}%`,
              transform: hoverCard.below ? 'translate(-50%, 14px)' : 'translate(-50%, -115%)',
            }}
          >
            <div className="kg-hover-name">{hoverCard.node.label}</div>
            <div className="kg-hover-meta">
              {hoverCard.node.kp_id && <span className="mono">{hoverCard.node.kp_id}</span>}
              <span>{TIER_CN[tierOf(hoverCard.node)] ?? hoverCard.node.tier}</span>
              <span>{hoverCard.node.state ?? '—'}</span>
            </div>
            {hoverCard.node.chapter && <div className="kg-hover-chapter">{hoverCard.node.chapter}</div>}
            <div className="kg-hover-action">点击查看关系 →</div>
          </div>
        )}
      </div>

      <div className="kg-overview-hint">
        <span>滚轮缩放 · 拖拽平移 · 悬停高亮 · 点节点进入焦点关系</span>
        <span className="kg-overview-hint-right">点章名可聚焦该章</span>
      </div>
    </>
  );
}
