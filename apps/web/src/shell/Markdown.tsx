import { useMemo } from 'react';
import { marked } from 'marked';
import katex from 'katex';
import 'katex/dist/katex.min.css';

marked.setOptions({ gfm: true, breaks: true });

/**
 * 轻量清洗：模型/知识库文本里若夹带原始 HTML，去掉可执行标签与事件属性。
 * 不是完整 sanitizer，但足以避免把 <script>/<iframe>/onerror 渲染进工作台。
 */
function scrub(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<iframe[\s\S]*?<\/iframe>/gi, '')
    .replace(/<(object|embed|link|meta|base)[^>]*>/gi, '')
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
    .replace(/(href|src)\s*=\s*(["'])\s*javascript:/gi, '$1=$2#');
}

function renderMath(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex, {
      displayMode,
      throwOnError: false,
      strict: 'ignore',
      output: 'htmlAndMathml',
    });
  } catch {
    return `<code>${tex.replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' })[c] || c)}</code>`;
  }
}

/** 行间公式：$$...$$ 或 \[...\] */
const blockMath = {
  name: 'blockMath',
  level: 'block',
  start(src: string) {
    const i = src.search(/\$\$|\\\[/);
    return i >= 0 ? i : undefined;
  },
  tokenizer(src: string) {
    const m = /^\$\$([\s\S]+?)\$\$/.exec(src) || /^\\\[([\s\S]+?)\\\]/.exec(src);
    if (!m) return undefined;
    return { type: 'blockMath', raw: m[0], text: (m[1] || '').trim() };
  },
  renderer(token: { text: string }) {
    return renderMath(token.text, true);
  },
};

/** 行内公式：\(...\) 与 $...$（$ 需要像公式才解析，避免和反应性单位 $ 冲突） */
const inlineMath = {
  name: 'inlineMath',
  level: 'inline',
  start(src: string) {
    const i = src.search(/\$|\\\(/);
    return i >= 0 ? i : undefined;
  },
  tokenizer(src: string) {
    const paren = /^\\\(([\s\S]+?)\\\)/.exec(src);
    if (paren) {
      return { type: 'inlineMath', raw: paren[0], text: (paren[1] || '').trim() };
    }
    const m = /^\$(?!\$)([^\n$]+?)\$(?!\$)/.exec(src);
    if (m) {
      const tex = (m[1] || '').trim();
      if (!tex || tex.length > 160) return undefined;
      // 只把"看起来像公式"的 $...$ 当数学；否则保留原文（如 "$0.2$"、价格）
      if (!/[\\^_=<>]|[α-ωΑ-Ω]/.test(tex)) return undefined;
      return { type: 'inlineMath', raw: m[0], text: tex };
    }
    return undefined;
  },
  renderer(token: { text: string }) {
    return renderMath(token.text, false);
  },
};

marked.use({ extensions: [blockMath, inlineMath] as unknown as Parameters<typeof marked.use>[0]['extensions'] });

export function Markdown({ text }: { text: string }) {
  const html = useMemo(() => {
    if (!text) return '';
    const parsed = marked.parse(text, { async: false }) as string;
    return scrub(parsed);
  }, [text]);
  return <div className="md" dangerouslySetInnerHTML={{ __html: html }} />;
}
