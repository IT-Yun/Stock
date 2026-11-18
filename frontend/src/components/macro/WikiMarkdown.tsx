// Wiki markdown 렌더러 — react-markdown + mermaid 다이어그램 자동 처리
import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    background: "#0a0a0a",
    primaryColor: "#1e293b",
    primaryTextColor: "#e2e8f0",
    primaryBorderColor: "#334155",
    lineColor: "#64748b",
    fontSize: "13px",
  },
  flowchart: { htmlLabels: true, curve: "basis" },
  securityLevel: "loose",
});

interface Props {
  content: string;
}

export default function WikiMarkdown({ content }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const blocks = containerRef.current.querySelectorAll<HTMLElement>("code.language-mermaid");
    blocks.forEach(async (codeEl, i) => {
      const pre = codeEl.parentElement;
      if (!pre || pre.dataset.mermaidProcessed === "1") return;
      const src = codeEl.textContent ?? "";
      const id = `mmd-${Date.now()}-${i}`;
      try {
        const { svg } = await mermaid.render(id, src);
        const wrapper = document.createElement("div");
        wrapper.className = "mermaid-rendered overflow-x-auto py-4";
        wrapper.innerHTML = svg;
        pre.replaceWith(wrapper);
      } catch (err) {
        // Render error — leave the original code block
        pre.dataset.mermaidProcessed = "1";
        console.warn("Mermaid render error:", err);
      }
    });
  }, [content]);

  return (
    <div ref={containerRef} className="prose-wiki max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (props) => <h1 className="text-2xl font-bold mt-8 mb-4 text-[var(--color-text-primary)]" {...props} />,
          h2: (props) => <h2 className="text-xl font-semibold mt-6 mb-3 text-[var(--color-text-primary)] border-b border-[var(--color-border)] pb-2" {...props} />,
          h3: (props) => <h3 className="text-lg font-semibold mt-5 mb-2 text-[var(--color-text-primary)]" {...props} />,
          h4: (props) => <h4 className="text-base font-semibold mt-4 mb-2 text-[var(--color-text-secondary)]" {...props} />,
          p: (props) => <p className="my-3 text-sm leading-relaxed text-[var(--color-text-secondary)]" {...props} />,
          ul: (props) => <ul className="my-3 ml-6 list-disc text-sm text-[var(--color-text-secondary)]" {...props} />,
          ol: (props) => <ol className="my-3 ml-6 list-decimal text-sm text-[var(--color-text-secondary)]" {...props} />,
          li: (props) => <li className="my-1" {...props} />,
          strong: (props) => <strong className="font-semibold text-[var(--color-text-primary)]" {...props} />,
          a: (props) => <a className="text-[#3b82f6] hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
          code: ({ className, children, ...props }: any) => {
            const isBlock = className?.startsWith("language-");
            if (isBlock) {
              return <code className={className} {...props}>{children}</code>;
            }
            return (
              <code
                className="px-1.5 py-0.5 rounded bg-white/5 text-[#fbbf24] text-[12px] font-mono"
                {...props}
              >
                {children}
              </code>
            );
          },
          pre: (props) => (
            <pre className="my-4 p-3 rounded-lg bg-black/40 border border-[var(--color-border)] overflow-x-auto text-[12px] font-mono text-[var(--color-text-secondary)]" {...props} />
          ),
          blockquote: (props) => (
            <blockquote className="my-3 pl-4 border-l-2 border-[#3b82f6]/50 text-[var(--color-text-secondary)] italic" {...props} />
          ),
          table: (props) => (
            <div className="my-4 overflow-x-auto">
              <table className="min-w-full text-sm border border-[var(--color-border)]" {...props} />
            </div>
          ),
          thead: (props) => <thead className="bg-white/5" {...props} />,
          th: (props) => <th className="px-3 py-2 text-left font-semibold text-[var(--color-text-primary)] border border-[var(--color-border)]" {...props} />,
          td: (props) => <td className="px-3 py-2 text-[var(--color-text-secondary)] border border-[var(--color-border)]" {...props} />,
          hr: () => <hr className="my-6 border-[var(--color-border)]" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
