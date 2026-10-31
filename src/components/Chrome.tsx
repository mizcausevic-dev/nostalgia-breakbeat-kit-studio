import { Menu, Moon, Sun, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { REPO } from "@/data";

export const NAV = [
  { href: "#lab", label: "Lab" },
  { href: "#compare", label: "Compare" },
  { href: "#map", label: "Kit map" },
  { href: "#mindmap", label: "Mindmap" },
  { href: "#harmony", label: "Harmony" },
  { href: "#sound", label: "Sound" },
  { href: "#pipeline", label: "Pipeline" },
  { href: "#validation", label: "Validation" },
  { href: "#origin", label: "Origin" },
  { href: "#brief", label: "Brief" },
  { href: "article.html", label: "Article" },
];

function useMode() {
  const [mode, setMode] = useState<"dark" | "light">("dark");
  useEffect(() => {
    const current = document.documentElement.dataset.mode === "light" ? "light" : "dark";
    setMode(current);
  }, []);
  function toggle() {
    const next = mode === "dark" ? "light" : "dark";
    document.documentElement.dataset.mode = next;
    localStorage.setItem("nostalgia-mode", next);
    setMode(next);
  }
  return { mode, toggle };
}

export function GitHubIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden>
      <path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.7 7.7 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

export function Logo({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="8" fill="currentColor" />
      <path d="M9 22V10h3.2l3.8 7.2L19.8 10H23v12h-2.4v-7.4L17.2 22h-2.4l-3.4-7.4V22H9z" fill="var(--bg)" />
    </svg>
  );
}

export function SiteHeader({ home = true }: { home?: boolean }) {
  const { mode, toggle } = useMode();
  const [open, setOpen] = useState(false);
  const link = (href: string) => (home || href.endsWith(".html") ? href : `./${href}`);
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_86%,transparent)] backdrop-blur-xl">
      <a className="skip" href={home ? "#lab" : "#article"}>
        {home ? "Skip to the kit lab" : "Skip to the article"}
      </a>
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <a href={home ? "#top" : "./"} className="flex min-w-0 items-center gap-2.5 font-semibold tracking-tight">
          <Logo className="size-8 shrink-0 text-[var(--ink)]" />
          <span className="text-sm leading-tight sm:text-base">
            <span className="sm:hidden">Nostalgia<br />Kits</span>
            <span className="hidden sm:inline">Nostalgia</span>
          </span>
        </a>
        <nav aria-label="Primary" className="ml-2 hidden items-center gap-1 lg:flex">
          {NAV.map((item) => (
            <a key={item.href} href={link(item.href)} className="rounded-md px-2.5 py-1.5 text-sm text-[var(--muted)] hover:bg-[var(--panel)] hover:text-[var(--ink)]">
              {item.label}
            </a>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1.5">
          <button type="button" onClick={toggle} className="inline-flex size-8 items-center justify-center rounded-full border border-[var(--line)]" aria-label={mode === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
            {mode === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
          <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex size-8 items-center justify-center rounded-full border border-[var(--line)]" aria-label="Source on GitHub">
            <GitHubIcon />
          </a>
          <button type="button" className="inline-flex size-8 items-center justify-center rounded-full border border-[var(--line)] lg:hidden" aria-expanded={open} aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen((value) => !value)}>
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>
      {open && (
        <nav aria-label="Sections" className="border-t border-[var(--line)] px-4 py-2 lg:hidden">
          {NAV.map((item) => (
            <a key={item.href} href={link(item.href)} onClick={() => setOpen(false)} className="block rounded-md px-3 py-2.5 text-base hover:bg-[var(--panel)]">
              {item.label}
            </a>
          ))}
        </nav>
      )}
    </header>
  );
}

export function SiteFooter({ home = true }: { home?: boolean }) {
  const page = (hash: string) => (home ? hash : `./${hash}`);
  const columns = [
    {
      title: "Project",
      links: [
        { label: "Source on GitHub", href: REPO },
        { label: "The article", href: "article.html" },
        { label: "Validation report", href: "data/validation-report.json" },
        { label: "Manifest", href: "data/manifest.json" },
      ],
    },
    {
      title: "Explore",
      links: [
        { label: "Kit lab", href: page("#lab") },
        { label: "Kit map", href: page("#map") },
        { label: "Harmony", href: page("#harmony") },
        { label: "Download the excerpts", href: page("#drop") },
      ],
    },
  ];
  return (
    <footer className="border-t border-[var(--line)]">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-4 lg:px-8">
        <div className="md:col-span-2">
          <p className="text-sm font-semibold">Nostalgia</p>
          <p className="mt-3 max-w-sm text-sm leading-6 text-[var(--muted)]">
            Eight original breakbeat kits and the builder that rendered them. The lab plays the demo excerpts, not a substitute synth.
          </p>
          <p className="mt-3 text-sm text-[var(--muted)]">
            Built by Miz Causevic at <a className="underline" href="https://kineticgain.com">Kinetic Gain</a>.
          </p>
        </div>
        {columns.map((column) => (
          <div key={column.title}>
            <p className="text-sm font-semibold">{column.title}</p>
            <ul className="mt-3 space-y-2 text-sm text-[var(--muted)]">
              {column.links.map((link) => (
                <li key={link.label}><a className="hover:text-[var(--ink)]" href={link.href}>{link.label}</a></li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="mx-auto max-w-7xl px-4 pb-10 text-xs leading-5 text-[var(--muted)] sm:px-6 lg:px-8">
        Code: MIT license. Kits: royalty-free in your own productions, not for redistribution as a pack. See LICENSE-KITS.md.
        Illustrations are generated for this project. No cookies, no analytics, no forms. Light or dark is kept in local storage.
        The 24-bit stem set is about 3.4 GB and is not in this repository.
      </p>
    </footer>
  );
}

export function Section({ id, children }: { id: string; children: ReactNode }) {
  return <section id={id} className="mx-auto max-w-7xl scroll-mt-20 px-4 py-14 sm:px-6 lg:px-8">{children}</section>;
}

export function SectionHeading({ index, label, title, highlight, children }: { index: string; label: string; title: string; highlight?: string; children: ReactNode }) {
  return (
    <div className="max-w-3xl">
      <p className="eyebrow">{index} · {label}</p>
      <h2 className="mt-3 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
        {title}{highlight ? " " : ""}
        {highlight && <span className="text-gradient">{highlight}</span>}
      </h2>
      <p className="mt-4 text-base leading-7 text-[var(--muted)] sm:text-lg">{children}</p>
    </div>
  );
}
