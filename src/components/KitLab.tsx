import { useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Download, Pause, Play, Search, X } from "lucide-react";
import { dawNotes, directions, kits, stems } from "@/data";
import loudness from "@/loudness.json";
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
  const meter = loudness.kits[kit.id as keyof typeof loudness.kits];
  const audible = stems.filter((stem) => !lab.off.includes(stem.id)).length;
  return (
    <Section id="lab">
      <SectionHeading index="01" label="Kit lab" title="Audition all eight." highlight="Hear the file, not a mockup.">
        The demo button plays eight seconds of the unmastered arrangement. Stems plays the same window from each arrangement stem, so you can mute the acid line or leave only the break. Those previews are not the 64-bar WAV stems. The 24-bit set is about 3.4 GB and is not hosted here.
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
          <div className="mt-4 flex flex-wrap items-center gap-2" role="group" aria-label="What to play">
            <ModeButton active={lab.audition === "demo"} onClick={() => lab.setAudition("demo")}>Demo excerpt</ModeButton>
            <ModeButton active={lab.audition === "stems"} onClick={() => lab.setAudition("stems")}>Stems</ModeButton>
          </div>
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
            <span className="ml-auto font-mono text-xs text-[var(--muted)]">
              {lab.audition === "stems" ? `${audible} of ${stems.length} stems` : "demo excerpt"}
              {lab.stemState === "loading" && lab.audition === "stems" ? " · reading" : ""}
            </span>
          </div>
          {lab.audition === "stems" && (
            <div className="mt-4">
              <div className="flex items-center justify-between gap-3">
                <p className="eyebrow">Arrangement stems</p>
                <button type="button" className="text-xs text-[var(--acid)]" onClick={lab.resetStems}>All stems</button>
              </div>
              <ul className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
                {stems.map((stem) => {
                  const on = !lab.off.includes(stem.id);
                  return (
                    <li key={stem.id} className="flex overflow-hidden rounded-xl border border-[var(--line)]">
                      <button type="button" aria-pressed={on} onClick={() => lab.toggleStem(stem.id)} className={`min-w-0 flex-1 px-2 py-2 text-left text-xs ${on ? "bg-[color-mix(in_srgb,var(--acid)_18%,transparent)]" : "text-[var(--muted)]"}`}>
                        {stem.label}
                      </button>
                      <button type="button" className="border-l border-[var(--line)] px-2 text-[0.65rem] uppercase tracking-wide text-[var(--muted)]" aria-label={`Solo ${stem.label}`} onClick={() => lab.soloStem(stem.id)}>Solo</button>
                    </li>
                  );
                })}
              </ul>
              {lab.stemState === "error" && <p role="alert" className="mt-2 text-sm text-[var(--amber)]">The stem previews did not load. The demo excerpt still plays.</p>}
              <p className="mt-2 text-xs leading-5 text-[var(--muted)]">Same 8-second window as the demo excerpt, cut from each stem WAV, then encoded for the browser. Summing them here is an audition. The zero-error stem sum is the WAV check, not this playback.</p>
            </div>
          )}
          <audio
            key={kit.id}
            ref={lab.audioRef}
            className={`mt-5 w-full ${lab.audition === "stems" ? "hidden" : ""}`}
            controls
            preload="none"
            src={kit.audio}
            onPlay={() => lab.mark(true)}
            onPause={() => lab.mark(false)}
          />
          <div className="mt-4 flex flex-wrap gap-2">
            <a className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={kit.audio} download><Download className="size-4" /> Excerpt</a>
            <a className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={kit.combinedMidi} download><Download className="size-4" /> Combined MIDI</a>
            <a className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={kit.midiZip} download><Download className="size-4" /> {kit.id} MIDI zip</a>
            <a className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] px-3 py-2 text-sm font-semibold" href="nostalgia-midi.zip" download><Download className="size-4" /> All MIDI</a>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-[var(--muted)]">
            Keys: <span className="kbd">Space</span> play or stop · <span className="kbd">←</span> <span className="kbd">→</span> or <span className="kbd">J</span> <span className="kbd">K</span> switch kit
          </p>
        </div>
        <LabAside kit={kit} meter={meter} />
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

function ModeButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" aria-pressed={active} onClick={onClick} className={`rounded-full px-3 py-1.5 text-sm ${active ? "bg-[var(--acid)] font-semibold text-[var(--bg)]" : "border border-[var(--line)]"}`}>
      {children}
    </button>
  );
}

function LabAside({ kit, meter }: { kit: (typeof kits)[number]; meter: { integratedLufs: number; truePeakDbfs: number; lraLu: number } }) {
  const [tab, setTab] = useState<"facts" | "daw" | "loudness">("facts");
  return (
    <aside className="border-t border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_45%,transparent)] p-4 sm:p-6 lg:border-l lg:border-t-0" aria-label="Kit details">
      <div className="flex gap-2" role="tablist" aria-label="Kit details">
        {(["facts", "loudness", "daw"] as const).map((id) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)} className={`rounded-full px-3 py-1 text-xs capitalize ${tab === id ? "bg-[var(--ink)] text-[var(--bg)]" : "text-[var(--muted)]"}`}>
            {id === "daw" ? "DAW" : id}
          </button>
        ))}
      </div>
      {tab === "facts" && (
        <dl className="mt-4 grid gap-2 font-mono text-[0.72rem]">
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
            ["Shared trim", kit.gain.toFixed(4)],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between gap-3">
              <dt className="text-[var(--muted)]">{label}</dt>
              <dd className="text-right">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {tab === "loudness" && (
        <div className="mt-4">
          <dl className="grid grid-cols-3 gap-2 text-center">
            <Meter label="Integrated" value={`${meter.integratedLufs.toFixed(1)} LUFS`} />
            <Meter label="True peak" value={`${meter.truePeakDbfs.toFixed(1)} dBFS`} />
            <Meter label="LRA" value={`${meter.lraLu.toFixed(1)} LU`} />
          </dl>
          <p className="mt-3 text-xs leading-5 text-[var(--muted)]">{loudness.scope} {loudness.meter}. {loudness.notInValidator} {loudness.previewFades}</p>
        </div>
      )}
      {tab === "daw" && (
        <div className="mt-4 space-y-3">
          {dawNotes.map((note) => (
            <div key={note.tool}>
              <h4 className="text-sm font-semibold">{note.tool}</h4>
              <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{note.body}</p>
            </div>
          ))}
          <p className="text-xs leading-5 text-[var(--muted)]">These notes describe the files. Live, FL Studio, and Logic were not opened in the environment that rendered the kits.</p>
        </div>
      )}
    </aside>
  );
}

function Meter({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--line)] px-2 py-2">
      <dt className="text-[0.65rem] uppercase tracking-wide text-[var(--muted)]">{label}</dt>
      <dd className="mono mt-1 text-xs">{value}</dd>
    </div>
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
