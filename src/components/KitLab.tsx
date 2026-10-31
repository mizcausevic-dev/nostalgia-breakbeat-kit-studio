import { useEffect, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Download, Pause, Play, Search, X } from "lucide-react";
import { directions, kits } from "@/data";
import { useLab } from "@/lab";
import { Section, SectionHeading } from "@/components/Chrome";

const DOT: Record<string, string> = {
  "Warehouse Pressure": "var(--acid)",
  "Acid Collision": "var(--amber)",
  "Rave Memory": "color-mix(in srgb, var(--acid) 55%, var(--amber))",
  "Concrete Funk": "var(--muted)",
};

export function KitLab() {
  const lab = useLab();
  const kit = lab.kit;
  const dirty = lab.query !== "" || lab.direction !== "all";
  useEffect(() => {
    if (!lab.armed) return;
    const audio = lab.audioRef.current;
    lab.clearArmed();
    if (!audio) return;
    void audio.play().catch(() => lab.mark(false));
  }, [kit.id, lab.armed, lab.audioRef, lab.clearArmed, lab.mark]);
  return (
    <Section id="lab">
      <SectionHeading index="01" label="Kit lab" title="Audition all eight." highlight="Hear the file, not a mockup.">
        Each clip is eight seconds of that kit’s unmastered 64-bar demo, cut from a named region. A 20 ms fade in and a 300 ms fade out exist only on the preview. The full stem set is 24-bit WAV and is not hosted here.
      </SectionHeading>

      <div className="panel mt-10 grid overflow-hidden lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 p-4 sm:p-6">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-[var(--line)] px-2 py-0.5 font-mono text-[0.7rem]">{kit.id}</span>
            <span className="inline-flex items-center gap-1.5 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-[var(--muted)]">
              <span className="size-2 rounded-full" style={{ background: DOT[kit.direction] }} />
              {kit.direction}
            </span>
          </div>
          <h3 className="mt-2 text-3xl font-semibold tracking-tight" aria-live="polite">{kit.name}</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{kit.blurb}</p>
          <p className="mono mt-3 text-xs text-[var(--muted)]">
            {kit.key} · {kit.bpm} BPM · excerpt from bar index {kit.startBar} · {kit.region}
          </p>
          <div className="mt-4 flex items-center gap-2">
            <button type="button" className="inline-flex size-10 items-center justify-center rounded-full border border-[var(--line)]" onClick={() => lab.step(-1)} aria-label="Previous kit">
              <ChevronLeft className="size-4" />
            </button>
            <button type="button" className="inline-flex h-10 min-w-28 items-center justify-center gap-2 rounded-xl bg-[var(--acid)] px-4 text-sm font-semibold text-[var(--bg)]" onClick={() => void lab.toggle()} aria-label={lab.playing ? "Pause" : `Play ${kit.name}`}>
              {lab.playing ? <Pause className="size-4" /> : <Play className="size-4" />}
              {lab.playing ? "Pause" : "Play"}
            </button>
            <button type="button" className="inline-flex size-10 items-center justify-center rounded-full border border-[var(--line)]" onClick={() => lab.step(1)} aria-label="Next kit">
              <ChevronRight className="size-4" />
            </button>
          </div>
          <audio
            key={kit.id}
            ref={lab.audioRef}
            className="mt-5 w-full"
            controls
            preload="none"
            src={kit.audio}
            onPlay={() => lab.mark(true)}
            onPause={() => lab.mark(false)}
          />
          <p className="mt-3 text-xs leading-relaxed text-[var(--muted)]">
            Keys: <span className="kbd">Space</span> play or stop · <span className="kbd">←</span> <span className="kbd">→</span> or <span className="kbd">J</span> <span className="kbd">K</span> switch kit
          </p>
        </div>
        <aside className="border-t border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_45%,transparent)] p-4 sm:p-6 lg:border-l lg:border-t-0" aria-label="File facts">
          <h4 className="eyebrow">File facts</h4>
          <dl className="mt-3 grid gap-2 font-mono text-[0.72rem]">
            {[
              ["Requested BPM", String(kit.bpm)],
              ["Effective BPM", kit.effective],
              ["Key", kit.key],
              ["Excerpt", "8 seconds"],
              ["Preview fades", "20 ms in, 300 ms out"],
              ["Start", `bar index ${kit.startBar}`],
              ["Region", kit.region],
              ["Bass near kick", `${Math.round(kit.kickShare * 100)}%`],
              ["Quiet / loud RMS", kit.quietRatio.toFixed(3)],
              ["Core V01 centroid", `${kit.centroidHz} Hz`],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between gap-3">
                <dt className="text-[var(--muted)]">{label}</dt>
                <dd className="text-right">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs leading-5 text-[var(--muted)]">This is the demo excerpt. It is not a resynthesis, and it is not the 64-bar stem.</p>
          <a className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={kit.audio} download>
            <Download className="size-4" /> {kit.id}.m4a
          </a>
        </aside>
      </div>

      <div className="mt-8 flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative lg:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[var(--muted)]" />
          <input
            value={lab.query}
            onChange={(event) => lab.setQuery(event.target.value)}
            placeholder="Search name, key, BPM…"
            aria-label="Search kits"
            className="h-9 w-full rounded-full border border-[var(--line)] bg-[var(--panel)] pl-9 pr-3 text-sm outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by direction">
          <FilterChip active={lab.direction === "all"} onClick={() => lab.setDirection("all")}>All directions</FilterChip>
          {directions.map((name) => (
            <FilterChip key={name} active={lab.direction === name} onClick={() => lab.setDirection(name)}>
              <span className="size-2 rounded-full" style={{ background: DOT[name] }} /> {name}
            </FilterChip>
          ))}
        </div>
        {dirty && (
          <button type="button" onClick={lab.resetFilters} className="inline-flex items-center gap-1 text-xs text-[var(--acid)] lg:ml-auto">
            <X className="size-3.5" /> Reset filters
          </button>
        )}
      </div>
      <p className="mt-4 text-xs text-[var(--muted)]" aria-live="polite">
        Showing <span className="font-semibold text-[var(--ink)]">{lab.visible.length}</span> of {kits.length} kits
      </p>
      {lab.visible.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-[var(--line)] p-10 text-center">
          <p className="font-medium">No kit matches these filters.</p>
          <button type="button" className="mt-4 rounded-full border border-[var(--line)] px-4 py-2 text-sm" onClick={lab.resetFilters}>Reset filters</button>
        </div>
      ) : (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {lab.visible.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              id={item.id}
              aria-current={item.id === kit.id ? "true" : undefined}
              onClick={(event) => {
                event.preventDefault();
                lab.select(item.id, { scroll: true });
              }}
              className={`rounded-2xl border bg-[var(--panel)] p-3.5 ${item.id === kit.id ? "border-[var(--acid)]" : "border-[var(--line)]"}`}
            >
              <div className="flex items-center justify-between font-mono text-[0.65rem] uppercase tracking-[0.14em] text-[var(--muted)]">
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full" style={{ background: DOT[item.direction] }} />
                  {item.id}
                </span>
                <span>{item.bpm} BPM</span>
              </div>
              <div className="mt-1.5 font-semibold tracking-tight">{item.name}</div>
              <div className="text-xs text-[var(--muted)]">{item.key} · {item.region}</div>
            </a>
          ))}
        </div>
      )}
    </Section>
  );
}

function FilterChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-xs font-medium ${active ? "border-[var(--acid)] bg-[color-mix(in_srgb,var(--acid)_18%,transparent)] text-[var(--ink)]" : "border-[var(--line)] text-[var(--muted)]"}`}
    >
      {children}
    </button>
  );
}
