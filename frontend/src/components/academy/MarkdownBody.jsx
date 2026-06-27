import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "loose" });

function MermaidBlock({ chart }) {
  const [svg, setSvg] = useState("");
  const wrapRef = React.useRef(null);
  useEffect(() => {
    let cancelled = false;
    const id = `mermaid-${Math.random().toString(36).slice(2)}`;
    mermaid.render(id, chart).then(({ svg: s }) => {
      if (!cancelled) setSvg(s);
    }).catch(() => {
      if (!cancelled) setSvg("");
    });
    return () => { cancelled = true; };
  }, [chart]);

  const exportSvg = () => {
    if (!svg) return;
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workflow.svg";
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportPng = () => {
    if (!svg || !wrapRef.current) return;
    const img = new Image();
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width || 800;
      canvas.height = img.height || 600;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#0d1117";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
      canvas.toBlob((png) => {
        if (!png) return;
        const pu = URL.createObjectURL(png);
        const a = document.createElement("a");
        a.href = pu;
        a.download = "workflow.png";
        a.click();
        URL.revokeObjectURL(pu);
      });
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  const printChart = () => {
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.write(`<html><body style="margin:0;padding:20px">${svg}</body></html>`);
    w.document.close();
    w.print();
  };

  if (!svg) return <pre className="ha-mermaid"><code>{chart}</code></pre>;
  return (
    <div className="ha-mermaid-wrap" ref={wrapRef}>
      <div className="ha-mermaid-toolbar">
        <button type="button" className="ha-btn" onClick={exportSvg}>SVG</button>
        <button type="button" className="ha-btn" onClick={exportPng}>PNG</button>
        <button type="button" className="ha-btn" onClick={printChart}>Print</button>
      </div>
      <div className="ha-mermaid" dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  );
}

function CopyButton({ text }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      type="button"
      className="ha-copy-btn"
      onClick={() => {
        navigator.clipboard?.writeText(text);
        setOk(true);
        setTimeout(() => setOk(false), 1500);
      }}
    >
      {ok ? "✓" : "Kopyala"}
    </button>
  );
}

export default function MarkdownBody({ content, onModuleLaunch, headingsRef }) {
  return (
    <div className="ha-content" ref={headingsRef}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h2: ({ children, ...props }) => {
            const id = String(children).toLowerCase().replace(/[^\wğüşıöç]+/gi, "-");
            return <h2 id={id} {...props}>{children}</h2>;
          },
          h3: ({ children, ...props }) => {
            const id = String(children).toLowerCase().replace(/[^\wğüşıöç]+/gi, "-");
            return <h3 id={id} {...props}>{children}</h3>;
          },
          a: ({ href, children, ...props }) => {
            if (href?.startsWith("hive://module/")) {
              const mod = href.replace("hive://module/", "");
              return (
                <button type="button" className="ha-launch-btn" onClick={() => onModuleLaunch?.(mod)}>
                  🚀 Aç — {children}
                </button>
              );
            }
            return <a href={href} target="_blank" rel="noreferrer" {...props}>{children}</a>;
          },
          img: ({ src, alt, title, ...props }) => (
            <figure className="ha-figure">
              <img src={src} alt={alt || ""} className="ha-screenshot-img" {...props} />
              {(title || alt) && <figcaption>{title || alt}</figcaption>}
            </figure>
          ),
          blockquote: ({ children }) => {
            const text = String(children);
            if (text.includes("Screenshot placeholder") || text.includes("📷")) {
              return <div className="ha-screenshot-placeholder">{children}</div>;
            }
            return <blockquote>{children}</blockquote>;
          },
          code({ inline, className, children, ...props }) {
            const text = String(children).replace(/\n$/, "");
            const lang = (className || "").replace("language-", "");
            if (!inline && lang === "mermaid") return <MermaidBlock chart={text} />;
            if (inline) return <code className={className} {...props}>{children}</code>;
            return (
              <div className="ha-code-wrap">
                <CopyButton text={text} />
                <pre><code className={className} {...props}>{children}</code></pre>
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
