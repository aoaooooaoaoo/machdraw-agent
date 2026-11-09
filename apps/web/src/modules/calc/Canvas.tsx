import type { CanvasProps } from '../registry';
import type { CalcData, CalcResult } from '../../lib/types';
import { Icon } from '../../shell/Icons';

/* ---------------------------------------------------------------- 数值格式化 */

const SUP: Record<string, string> = {
  '0': '⁰',
  '1': '¹',
  '2': '²',
  '3': '³',
  '4': '⁴',
  '5': '⁵',
  '6': '⁶',
  '7': '⁷',
  '8': '⁸',
  '9': '⁹',
  '-': '⁻',
  '+': '⁺',
};

/** 10 的幂 → Unicode 上标（如 3.33×10⁻⁴）。 */
function sup(n: number): string {
  return String(n)
    .split('')
    .map((c) => SUP[c] ?? c)
    .join('');
}

/**
 * 展示用数值格式：
 * - 字符串原样输出（后端可能直接给 "1.0021" / "0.893"）；
 * - 常规量级用 4 位小数去尾零；
 * - 很小/很大的量用 a×10ⁿ 形式，避免右栏里出现 `3.3333e-4`。
 */
function fmtValue(v: number | string | undefined | null): string {
  if (v === undefined || v === null || v === '') return '—';
  if (typeof v === 'string') return v;
  if (!Number.isFinite(v)) return String(v);
  const abs = Math.abs(v);
  if (abs === 0) return '0';
  if (abs >= 1e-3 && abs < 1e5) {
    const fixed = v.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
    return fixed === '-0' ? '0' : fixed;
  }
  const exp = Math.floor(Math.log10(abs));
  const mant = Number((v / 10 ** exp).toPrecision(3));
  return `${mant}×10${sup(exp)}`;
}

/** 结论条配色：先判「次临界 / 超临界」，再判普通「临界」。 */
function verdictTone(level: string): string {
  if (/次临界|亚临界|低于|不合格|不满足|失败/.test(level)) return 'is-under';
  if (/超临界|超过|超限|过深/.test(level)) return 'is-over';
  if (/临界|满足|合格/.test(level)) return 'is-ok';
  return 'is-neutral';
}

/* ---------------------------------------------------------------- 主组件 */

/** calc 画布：输入表 → 公式步 → 结果表 → 结论条 → 依据（可选 SVG / 说明）。 */
export function CalcCanvas({ artifact, demo }: CanvasProps) {
  const data = (artifact.data || {}) as CalcData;
  const inputs = Array.isArray(data.inputs) ? data.inputs : [];
  const formulas = Array.isArray(data.formulas) ? data.formulas : [];
  const results: CalcResult[] = Array.isArray(data.results) ? data.results : [];
  const refs = Array.isArray(data.refs) ? data.refs : [];
  const verdict = data.verdict;
  const hasSvg = typeof data.svg === 'string' && data.svg.trim().length > 0;
  const hasContent =
    inputs.length > 0 || formulas.length > 0 || results.length > 0 || Boolean(verdict) || hasSvg;

  if (!hasContent) {
    return (
      <div className="canvas-body">
        <div className="canvas-empty-inline">
          <Icon name="alert" size={20} />
          <p>calc artifact 还没有输入 / 公式 / 结果字段，无法渲染计算卡。</p>
          <pre className="json-pre">{JSON.stringify(data, null, 2).slice(0, 1600)}</pre>
        </div>
      </div>
    );
  }

  return (
    <div className="canvas-body calc-body">
      <div className="calc-head">
        <div className="calc-headline">
          <span className="calc-title">{data.title ?? '确定性计算'}</span>
          <span className="chip chip-type mono">calc</span>
          {demo && <span className="chip chip-demo">示例</span>}
        </div>
      </div>

      {inputs.length > 0 && (
        <section className="calc-section">
          <div className="calc-section-title">输入</div>
          <div className="tol-table-wrap">
            <table className="tol-table">
              <thead>
                <tr>
                  <th>量</th>
                  <th>取值</th>
                  <th>单位</th>
                </tr>
              </thead>
              <tbody>
                {inputs.map((item, i) => (
                  <tr key={`${item.name}_${i}`}>
                    <td>{item.name}</td>
                    <td className="mono">{fmtValue(item.value)}</td>
                    <td className="mono">{item.unit ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {formulas.length > 0 && (
        <section className="calc-section">
          <div className="calc-section-title">计算步骤</div>
          <ol className="calc-formulas">
            {formulas.map((f, i) => (
              <li className="calc-formula" key={`${f.step}_${i}`}>
                <span className="calc-step-no">{i + 1}</span>
                <div className="calc-formula-main">
                  <code className="calc-formula-code">{f.step}</code>
                  {f.note && <span className="calc-formula-note">{f.note}</span>}
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {results.length > 0 && (
        <section className="calc-section">
          <div className="calc-section-title">结果</div>
          <div className="tol-table-wrap">
            <table className="tol-table">
              <thead>
                <tr>
                  <th>量</th>
                  <th>数值</th>
                  <th>单位</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                {results.map((item, i) => (
                  <tr key={`${item.name}_${i}`}>
                    <td>{item.name}</td>
                    <td className="mono calc-result-value">{fmtValue(item.value)}</td>
                    <td className="mono">{item.unit ?? '—'}</td>
                    <td className="calc-result-note">{item.note ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {verdict && (
        <div className={`calc-verdict ${verdictTone(verdict.level)}`} role="status">
          <span className="calc-verdict-label">结论</span>
          <strong className="calc-verdict-level">{verdict.level}</strong>
          {verdict.note && <span className="calc-verdict-note">{verdict.note}</span>}
        </div>
      )}

      {refs.length > 0 && (
        <div className="calc-refs">
          <span className="tol-note-label">依据</span>
          {refs.map((r) => (
            <span className="chip chip-doc" key={r}>
              {r}
            </span>
          ))}
        </div>
      )}

      {data.note && (
        <div className="tol-note">
          <span className="tol-note-label">说明</span>
          <span>{data.note}</span>
        </div>
      )}

      {hasSvg && (
        <div className="calc-section">
          <div className="calc-section-title">图示</div>
          <div className="calc-svg" dangerouslySetInnerHTML={{ __html: data.svg as string }} />
        </div>
      )}
    </div>
  );
}

export default CalcCanvas;
