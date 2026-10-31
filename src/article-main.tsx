import { StrictMode, useMemo } from "react";
import { createRoot } from "react-dom/client";
import { SiteFooter, SiteHeader } from "@/components/Chrome";
import source from "../article/technical.md?raw";
import "./index.css";

function parse(markdown: string) {
  const match = markdown.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  const meta: Record<string, string> = {};
  if (!match) return { meta, body: markdown };
  for (const line of match[1].split("\n")) {
    const cut = line.indexOf(":");
    if (cut < 1) continue;
    meta[line.slice(0, cut).trim()] = line.slice(cut + 1).trim().replace(/^"|"$/g, "");
  }
  return { meta, body: match[2].trim() };
}

function inline(text: string) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((bit, index) => {
    if (bit.startsWith("`") && bit.endsWith("`")) return <code key={index}>{bit.slice(1, -1)}</code>;
    if (bit.startsWith("**") && bit.endsWith("**")) return <strong key={index}>{bit.slice(2, -2)}</strong>;
    return bit;
  });
}

function Article() {
  const { meta, body } = useMemo(() => parse(source), []);
  const parts = body.split(/\n{2,}/);
  return (
    <>
      <SiteHeader home={false} />
      <main id="article" className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <p className="eyebrow">Technical readers</p>
        <h1 className="mt-3 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">{meta.title}</h1>
        {meta.subtitle && <p className="mt-4 text-lg leading-8 text-[var(--muted)]">{meta.subtitle}</p>}
        <div className="article-body mt-8">
          {parts.map((part, index) => {
            if (part.startsWith("## ")) return <h2 key={index}>{part.slice(3)}</h2>;
            if (part.startsWith("# ")) return <h2 key={index}>{part.slice(2)}</h2>;
            if (part.startsWith("```")) {
              const code = part.replace(/^```[a-z]*\n?/, "").replace(/```$/, "");
              return <pre key={index}><code>{code}</code></pre>;
            }
            if (part.startsWith("- ")) {
              return (
                <ul key={index}>
                  {part.split("\n").map((line) => <li key={line}>{inline(line.replace(/^- /, ""))}</li>)}
                </ul>
              );
            }
            return <p key={index}>{inline(part)}</p>;
          })}
        </div>
      </main>
      <SiteFooter home={false} />
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Article />
  </StrictMode>,
);
