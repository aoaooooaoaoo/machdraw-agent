import { useEffect, useMemo, useState } from 'react';
import type { CanvasProps } from '../registry';
import type { EvidenceArtifactData, EvidenceItem, FigureItem } from '../../lib/types';
import { useAppStore } from '../../lib/store';
import { Icon } from '../../shell/Icons';

function pct(score: number): number {
  if (!Number.isFinite(score)) return 0;
  // score 是 0..1 的相关度（实测样例出现过 1.0）
  return Math.max(0, Math.min(100, Math.round(score * 100)));
}

/* ---------------------------------------------------------------- 配图匹配 */

function figureUrl(figure: FigureItem): string {
  return `/figures/${figure.file}`;
}

/**
 * 把 artifact 里的 figures 分配给最相关的证据卡。
 * 后端 figures 是"本轮检索相关图"的平铺列表，没有 chunk_id 直连，
 * 这里用 章节前缀 + structure_tags 在卡片文本里的命中做贪心匹配；
 * 分不出去的图再顺序补给还没配图的卡片，保证「每张图都被看到、同一张不重复」。
 */
function matchFigures(evidences: EvidenceItem[], figures: FigureItem[]): Map<number, FigureItem> {
  const uniq: FigureItem[] = [];
  const seen = new Set<string>();
  for (const f of figures) {
    if (!f || !f.figure_id || !f.file || seen.has(f.figure_id)) continue;
    seen.add(f.figure_id);
    uniq.push(f);
  }

  const result = new Map<number, FigureItem>();
  const used = new Set<string>();
  const score = (item: EvidenceItem, fig: FigureItem): number => {
    const section = (item.section || '').toLowerCase();
    const text = `${item.documentTitle} ${item.section} ${item.content}`.toLowerCase();
    let s = 0;
    // 章节前缀：属于同一章，但区分度不如结构词，权重低
    if (fig.chapter && section.includes(fig.chapter.toLowerCase())) s += 2;
    // 结构标签：出现在章节里权重最高（说明这一节就在讲这个图），正文里次之
    for (const tag of fig.structure_tags || []) {
      if (!tag) continue;
      const low = tag.toLowerCase();
      if (section.includes(low)) s += 3;
      else if (text.includes(low)) s += 1;
    }
    // 图题里的实义片段（如"三等规律"）出现在章节里，说明是这一节的主图
    for (const token of (fig.title || '').split(/[的与和、（）()：:·\s+]+/)) {
      if (token.length >= 2 && section.includes(token.toLowerCase())) s += 3;
    }
    return s;
  };

  // 贪心分配：每轮取全局最高分的 (卡, 图)
  for (;;) {
    let best: { card: number; fig: FigureItem; pts: number } | null = null;
    for (let i = 0; i < evidences.length; i += 1) {
      if (result.has(i)) continue;
      for (const fig of uniq) {
        if (used.has(fig.figure_id)) continue;
        const pts = score(evidences[i], fig);
        if (pts > 0 && (!best || pts > best.pts)) best = { card: i, fig, pts };
      }
    }
    if (!best) break;
    result.set(best.card, best.fig);
    used.add(best.fig.figure_id);
  }

  // 余图顺序补给空卡（避免"图库有图却没显示"）
  let card = 0;
  for (const fig of uniq) {
    if (used.has(fig.figure_id)) continue;
    while (card < evidences.length && result.has(card)) card += 1;
    if (card >= evidences.length) break;
    result.set(card, fig);
    used.add(fig.figure_id);
    card += 1;
  }
  return result;
}

/* ---------------------------------------------------------------- 配图组件 */

function FigureBlock({ figure, onOpen }: { figure: FigureItem; onOpen: (f: FigureItem) => void }) {
  const [captionOpen, setCaptionOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const caption = figure.caption || '';
  const longCaption = caption.length > 56;

  return (
    <div className="ev-figure">
      <button
        type="button"
        className="ev-figure-imgwrap"
        onClick={() => onOpen(figure)}
        title="点击查看大图"
      >
        {failed ? (
          <span className="ev-figure-fail">
            <Icon name="alert" size={14} /> 配图加载失败：{figure.file}
          </span>
        ) : (
          <img
            className="ev-figure-img"
            src={figureUrl(figure)}
            alt={figure.title}
            loading="lazy"
            onError={() => setFailed(true)}
          />
        )}
        <span className="ev-figure-zoom">
          <Icon name="expand" size={12} /> 放大
        </span>
      </button>

      <div className="ev-figure-meta">
        <div className="ev-figure-title">
          <Icon name="pin" size={12} />
          <span>{figure.title}</span>
        </div>
        {caption && (
          <div className={`ev-figure-caption ${captionOpen ? 'is-open' : ''}`}>
            <p>{caption}</p>
            {longCaption && (
              <button className="link-btn" type="button" onClick={() => setCaptionOpen((v) => !v)}>
                <Icon name="chevron" size={11} className={captionOpen ? 'is-open' : ''} />
                {captionOpen ? '收起图注' : '展开图注'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function FigureLightbox({ figure, onClose }: { figure: FigureItem; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fig-mask" role="dialog" aria-modal="true" aria-label={figure.title} onClick={onClose}>
      <div className="fig-modal" onClick={(e) => e.stopPropagation()}>
        <div className="fig-modal-head">
          <div className="fig-modal-heading">
            <div className="fig-modal-title">{figure.title}</div>
            {figure.chapter && <div className="fig-modal-chapter">{figure.chapter}</div>}
          </div>
          <button className="icon-btn" type="button" onClick={onClose} aria-label="关闭大图">
            <Icon name="x" size={18} />
          </button>
        </div>

        {/* 自绘图 SVG 背景透明、线条深色 → 大图也给浅色底 */}
        <div className="fig-modal-img">
          <img src={figureUrl(figure)} alt={figure.title} />
        </div>

        {figure.caption && <p className="fig-modal-caption">{figure.caption}</p>}

        <div className="fig-modal-foot">
          {figure.source && <span className="chip">{figure.source}</span>}
          {figure.license && <span className="chip chip-doc">许可：{figure.license}</span>}
          {Array.isArray(figure.structure_tags) && figure.structure_tags.length > 0 && (
            <span className="fig-modal-tags">
              {figure.structure_tags.map((t) => (
                <span className="chip" key={t}>
                  {t}
                </span>
              ))}
            </span>
          )}
          <span className="mono fig-modal-id">{figure.figure_id}</span>
          <span className="fig-modal-hint">Esc 关闭</span>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- 证据卡 */

function EvidenceCard({
  item,
  index,
  figure,
  onAsk,
  onOpenFigure,
}: {
  item: EvidenceItem;
  index: number;
  figure?: FigureItem;
  onAsk: (text: string) => void;
  onOpenFigure: (f: FigureItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const long = (item.content || '').length > 180;
  const score = pct(item.score);

  const askText = `围绕证据【${index}】《${item.documentTitle}》${item.section ? `· ${item.section}` : ''}${
    item.chunkId ? `（${item.chunkId}）` : ''
  } 这段原文继续追问：`;

  return (
    <article className="ev-card">
      <header className="ev-card-head">
        <span className="ev-index">{index}</span>
        <div className="ev-title-wrap">
          <h4 className="ev-title" title={item.documentTitle}>
            {item.documentTitle}
          </h4>
          <div className="ev-meta">
            {item.category && <span className="chip chip-cat">{item.category}</span>}
            {item.section && <span className="ev-section">{item.section}</span>}
          </div>
        </div>
        {figure && <span className="ev-figure-badge">配图</span>}
      </header>

      <div className="ev-ident">
        <span className="mono ev-chunk" title="chunk_id（可回翻原文）">
          {item.chunkId}
        </span>
        {item.kbNo && <span className="chip">{item.kbNo}</span>}
        {item.clause && <span className="chip">第 {item.clause} 条</span>}
        {typeof item.page === 'number' && <span className="chip">p{item.page}</span>}
      </div>

      <div className="ev-score">
        <div className="ev-score-head">
          <span>相关度</span>
          <span className="mono">{score}%</span>
        </div>
        <div className="bar">
          <div className="bar-fill" style={{ width: `${score}%` }} />
        </div>
      </div>

      <div className={`ev-content ${open ? 'is-open' : ''}`}>
        <p>{item.content || item.snippet}</p>
      </div>

      {figure && <FigureBlock figure={figure} onOpen={onOpenFigure} />}

      <footer className="ev-card-foot">
        {long && (
          <button className="link-btn" type="button" onClick={() => setOpen((v) => !v)}>
            <Icon name="expand" size={12} />
            {open ? '收起原文' : '展开全文'}
          </button>
        )}
        <button className="link-btn link-accent" type="button" onClick={() => onAsk(askText)}>
          <Icon name="quote" size={12} />
          围绕此段追问
        </button>
      </footer>
    </article>
  );
}

/* ---------------------------------------------------------------- 画布 */

/** evidence 画布：证据卡列表（序号 / 文档 / 章节 / chunk_id / 相关度 / 展开 / 追问 / 自绘配图）。 */
export function EvidenceCanvas({ artifact, onAsk, demo }: CanvasProps) {
  const data = (artifact.data || {}) as EvidenceArtifactData;
  const evidences = useMemo(() => (Array.isArray(data.evidences) ? data.evidences : []), [data]);
  const figures = useMemo(() => (Array.isArray(data.figures) ? data.figures : []), [data]);
  const figureByCard = useMemo(() => matchFigures(evidences, figures), [evidences, figures]);
  const coverage = typeof data.coverage === 'number' ? data.coverage : 0;
  const coveragePct = Math.round(coverage * 1000) / 10;
  const chunkCoverage =
    typeof data.chunkCoverage === 'number' ? Math.round(data.chunkCoverage * 1000) / 10 : null;

  const [preview, setPreview] = useState<FigureItem | null>(null);
  // 门控阈值以后端 /api/health 的 gate_tau 为准（本课程标定为 0.40），不要在前端写死
  const gateTau = useAppStore((s) => s.health?.gate_tau) ?? 0.4;

  return (
    <div className="canvas-body">
      <div className="ev-summary">
        <div className="ev-summary-top">
          <div>
            <div className="ev-query-label">检索问题</div>
            <div className="ev-query">{data.query || '（未提供 query）'}</div>
          </div>
          <div className="ev-summary-tags">
            {figures.length > 0 && (
              <span className="chip chip-figure" title="本轮命中的自绘教学图">
                <Icon name="pin" size={11} /> 配图 {figures.length} 张
              </span>
            )}
            {demo && <span className="chip chip-demo">示例</span>}
          </div>
        </div>

        <div className="ev-stats">
          <div className="ev-stat">
            <span className="ev-stat-num">{evidences.length}</span>
            <span className="ev-stat-label">段证据</span>
          </div>
          <div className="ev-stat">
            <span className="ev-stat-num">{data.totalDocs ?? '—'}</span>
            <span className="ev-stat-label">份文档入库</span>
          </div>
          {chunkCoverage !== null && (
            <div className="ev-stat" title="双门控第二道信号：命中证据块对查询的覆盖比例">
              <span className="ev-stat-num">{chunkCoverage}%</span>
              <span className="ev-stat-label">chunk 覆盖率</span>
            </div>
          )}
          <div className="ev-stat ev-stat-bar">
            <div className="ev-stat-bar-head">
              <span className="ev-stat-label">IDF 覆盖率（门控指标 τ={'>'}{gateTau.toFixed(2)}）</span>
              <span className="mono">{coveragePct}%</span>
            </div>
            <div className="bar bar-lg">
              <div
                className={`bar-fill ${coverage < gateTau ? 'is-warn' : ''}`}
                style={{ width: `${Math.min(100, coveragePct)}%` }}
              />
            </div>
          </div>
        </div>

        {data.gated && (
          <div className="ev-gated">
            <Icon name="alert" size={13} />
            覆盖率低于门限，后端按"知识库未收录"处理——这是门控生效，不是检索失败。
          </div>
        )}
      </div>

      {evidences.length === 0 ? (
        <div className="canvas-empty-inline">
          <Icon name="book" size={20} />
          <p>本轮没有命中证据段。可以换个关键词，或确认知识库已装载。</p>
        </div>
      ) : (
        <div className="ev-list">
          {evidences.map((item, i) => (
            <EvidenceCard
              key={item.chunkId || `${i}`}
              item={item}
              index={i + 1}
              figure={figureByCard.get(i)}
              onAsk={onAsk}
              onOpenFigure={setPreview}
            />
          ))}
        </div>
      )}

      {Array.isArray(data.documents) && data.documents.length > 0 && (
        <div className="ev-docs">
          <div className="ev-docs-label">命中文档</div>
          <div className="ev-docs-list">
            {data.documents.map((d) => (
              <span className="chip chip-doc" key={d.id} title={d.category}>
                {d.title}
              </span>
            ))}
          </div>
        </div>
      )}

      {preview && <FigureLightbox figure={preview} onClose={() => setPreview(null)} />}
    </div>
  );
}
