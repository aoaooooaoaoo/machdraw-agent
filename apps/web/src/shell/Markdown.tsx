import { useMemo } from 'react';
import { marked } from 'marked';

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

export function Markdown({ text }: { text: string }) {
  const html = useMemo(() => {
    if (!text) return '';
    const parsed = marked.parse(text, { async: false }) as string;
    return scrub(parsed);
  }, [text]);
  return <div className="md" dangerouslySetInnerHTML={{ __html: html }} />;
}
