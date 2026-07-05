import { useMemo } from 'react';
import { marked } from 'marked';
import katex from 'katex';
import { CodeBlock } from './CodeBlock';
import type { SearchSource } from '../../types/session';

interface Props {
  content: string;
  searchSources?: SearchSource[];
}

function renderMath(text: string): string {
  let result = text;

  // \begin{xxx}...\end{xxx} 环境（align, equation, gather, matrix 等）
  result = result.replace(/\\begin\{(\w+)\}([\s\S]*?)\\end\{\1\}/gs, (match, _env, content) => {
    try {
      return katex.renderToString(`\\begin{${_env}}${content}\\end{${_env}}`, { displayMode: true, throwOnError: false });
    } catch {
      return match;
    }
  });

  // \[...\] 显示公式
  result = result.replace(/\\\[([\s\S]+?)\\\]/gs, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false });
    } catch {
      return _;
    }
  });

  // $$...$$ 显示公式
  result = result.replace(/\$\$([\s\S]+?)\$\$/gs, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false });
    } catch {
      return _;
    }
  });

  // \(...\) 行内公式
  result = result.replace(/\\\((.+?)\\\)/gs, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
    } catch {
      return _;
    }
  });

  // $...$ 行内公式（最后匹配，避免误吞已有 HTML 中的 $）
  result = result.replace(/\$(.+?)\$/gs, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
    } catch {
      return _;
    }
  });

  return result;
}

function renderCitations(html: string, sources?: SearchSource[]): string {
  if (!sources || sources.length === 0) return html;
  return html.replace(
    /\[(\d+)\]/g,
    (_, num) => {
      const src = sources.find((s) => s.index === Number(num));
      if (!src) return `[${num}]`;
      const url = src.url.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return `<sup><a href="${url}" target="_blank" rel="noopener noreferrer" class="citation-badge text-accent no-underline hover:underline cursor-pointer font-medium">[${num}]</a></sup>`;
    },
  );
}

export function MarkdownRenderer({ content, searchSources }: Props) {
  const html = useMemo(() => {
    const withMath = renderMath(content);
    const withCitations = renderCitations(withMath, searchSources);
    const raw = marked.parse(withCitations, { async: false, gfm: true }) as string;
    return raw;
  }, [content, searchSources]);

  const segments = useMemo(() => {
    const parts: { type: 'code' | 'html'; code?: string; lang?: string; html?: string }[] = [];
    const codeBlockRegex = /<pre><code class="language-(\w*)">([\s\S]*?)<\/code><\/pre>/g;
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(html)) !== null) {
      if (match.index > lastIndex) {
        parts.push({ type: 'html', html: html.slice(lastIndex, match.index) });
      }
      parts.push({ type: 'code', code: match[2].replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'"), lang: match[1] || undefined });
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < html.length) {
      parts.push({ type: 'html', html: html.slice(lastIndex) });
    }

    return parts;
  }, [html]);

  return (
    <div className="markdown-body text-sm leading-relaxed text-text [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mb-1 [&_blockquote]:border-l-2 [&_blockquote]:border-accent/30 [&_blockquote]:pl-4 [&_blockquote]:text-text-muted [&_blockquote]:italic [&_a]:text-accent [&_a]:underline [&_a:hover]:text-accent-hover [&_table]:border-collapse [&_table]:my-3 [&_th]:border [&_th]:border-border [&_th]:px-3 [&_th]:py-1.5 [&_th]:bg-surface [&_td]:border [&_td]:border-border [&_td]:px-3 [&_td]:py-1.5 [&_hr]:border-border [&_hr]:my-4 [&_img]:rounded [&_img]:max-w-full [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:my-3 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:my-2 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:my-2 [&_h4]:text-sm [&_h4]:font-medium [&_h4]:my-2 [&_h5]:text-sm [&_h5]:font-medium [&_h5]:my-1 [&_h6]:text-sm [&_h6]:font-medium [&_h6]:my-1 [&_code:not(pre_code)]:px-1.5 [&_code:not(pre_code)]:py-0.5 [&_code:not(pre_code)]:text-xs [&_code:not(pre_code)]:rounded [&_code:not(pre_code)]:bg-accent-subtle [&_code:not(pre_code)]:font-mono [&_code:not(pre_code)]:text-accent">
      {segments.map((seg, i) =>
        seg.type === 'code' ? (
          <CodeBlock key={i} code={seg.code || ''} lang={seg.lang} />
        ) : (
          <div key={i} dangerouslySetInnerHTML={{ __html: seg.html || '' }} />
        ),
      )}
    </div>
  );
}
