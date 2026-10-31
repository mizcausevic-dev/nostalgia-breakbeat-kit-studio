import { Download, Pause, Play, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { checks, directions, kits, numerals, pipeline, REPO, roles } from "@/data";
import { useLab } from "@/lab";
import { Section, SectionHeading } from "@/components/Chrome";

export function Hero() {
  const lab = useLab();
  const kit = kits[0];
  const playing = lab.playing && lab.kit.id === kit.id;
  return (
    <div id="top" className="mx-auto max-w-7xl px-4 pt-6 sm:px-6 sm:pt-10 lg:px-8">
      <div className="panel relative overflow-hidden">
        <img
          src="images/hero-warehouse.jpg"
          alt="Empty concrete warehouse with one amber work light, a floor tom, and a coiled cable."
          width={1280}
          height={720}
          className="absolute inset-0 h-full w-full object-cover object-[70%_center] opacity-55 md:opacity-90"
        />
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(90deg, var(--panel) 0%, color-mix(in srgb, var(--panel) 88%, transparent) 42%, color-mix(in srgb, var(--panel) 28%, transparent) 72%, transparent 100%), linear-gradient(0deg, var(--panel) 0%, transparent 40%)",
          }}
        />
        <div className="relative px-5 pb-6 pt-10 sm:px-10 sm:pt-16 lg:px-14">
          <div className="max-w-2xl">
            <p className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_60%,transparent)] px-3 py-1 font-mono text-[0.68rem] uppercase tracking-[0.2em] backdrop-blur">
              <span className="pulse-dot size-1.5 rounded-full bg-[var(--acid)]" />
              8 breakbeat kits · excerpt download
            </p>
            <h1 className="mt-6 text-[2.6rem] font-bold leading-[1.02] tracking-tight text-balance sm:text-6xl lg:text-7xl">
              Eight kits for the <span className="text-gradient">warehouse floor.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-[var(--muted)] sm:text-lg">
              Nostalgia is original breakbeat and big-beat material: synthesized drums, bass, hooks, stabs, and acid lines. Audition every demo excerpt here, then take the MIDI into your session.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="inline-flex h-11 items-center gap-2 rounded-xl bg-[var(--acid)] px-5 text-sm font-semibold text-[var(--bg)]"
                onClick={() => lab.play(kit.id)}
              >
                {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
                {playing ? "Pause" : "Play"} {kit.id} {kit.name}
              </button>
              <a className="inline-flex h-11 items-center gap-2 rounded-xl border border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_55%,transparent)] px-5 text-sm font-semibold backdrop-blur" href="nostalgia-excerpts.zip" download>
                <Download className="size-4" /> Download the excerpts
              </a>
            </div>
            <a href="#validation" className="mt-4 inline-flex items-center gap-2 text-sm text-[var(--muted)] hover:text-[var(--ink)]">
              <ShieldCheck className="size-4 text-[var(--acid)]" />
              0 errors on the files that were reopened. 9 notes, including K01’s trim.
            </a>
          </div>
          <dl className="mt-12 grid grid-cols-2 overflow-hidden rounded-xl border border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_72%,transparent)] backdrop-blur sm:grid-cols-4 sm:divide-x sm:divide-[var(--line)]">
            {[
              ["0 errors", "validation, files reopened"],
              ["8", "kits"],
              ["192", "core identities"],
              ["112–136", "BPM"],
            ].map(([value, label]) => (
              <div key={label} className="px-4 py-4">
                <dt className="text-xs text-[var(--muted)]">{label}</dt>
                <dd className="mt-1 text-2xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
}

export function Marquee() {
  const lab = useLab();
  const row = [...kits, ...kits];
  return (
    <div className="marquee relative mt-10 overflow-hidden border-y border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_70%,transparent)] py-3" aria-label="All eight kits">
      <div className="marquee-track gap-8 font-mono text-xs uppercase tracking-[0.18em]">
        {row.map((kit, index) => (
          <button
            key={`${kit.id}-${index}`}
            type="button"
            tabIndex={index < kits.length ? 0 : -1}
            aria-hidden={index >= kits.length}
            onClick={() => lab.select(kit.id, { scroll: true })}
            className="mx-4 flex shrink-0 items-center gap-2 whitespace-nowrap text-[var(--muted)] hover:text-[var(--ink)]"
          >
            <span className="size-1.5 rounded-full bg-[var(--amber)]" />
            <span className="text-[var(--ink)]">{kit.id}</span> {kit.name}
            <span className="opacity-60">{kit.bpm}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function KitMap() {
  const lab = useLab();
  const maxX = 0.7;
  const maxY = 0.9;
  const kit = lab.kit;
  return (
    <Section id="map">
      <SectionHeading index="02" label="Kit map" title="Eight kits, plotted from the score review.">
        Horizontal is the share of bass note-ons within about 20 ms of a kick. Vertical is the quiet-region RMS divided by the loudest core-region RMS. Both numbers come from the musical review. They are not a listening score.
      </SectionHeading>
      <div className="panel mt-8 overflow-x-auto p-4">
        <svg viewBox="0 0 720 420" role="img" aria-label="Scatter plot of the eight kits" className="min-w-[640px]">
          <line x1="60" y1="30" x2="60" y2="360" stroke="currentColor" opacity="0.3" />
          <line x1="60" y1="360" x2="690" y2="360" stroke="currentColor" opacity="0.3" />
          <text x="300" y="400" fill="currentColor" fontSize="12">Bass notes near a kick</text>
          <text x="16" y="200" fill="currentColor" fontSize="12" transform="rotate(-90 16 200)">Quiet / loud</text>
          {kits.map((item) => {
            const x = 60 + (item.kickShare / maxX) * 620;
            const y = 360 - (item.quietRatio / maxY) * 320;
            const active = item.id === kit.id;
            return (
              <g key={item.id} onClick={() => lab.select(item.id)} className="cursor-pointer">
                <circle cx={x} cy={y} r={active ? 10 : 7} fill={active ? "var(--amber)" : "var(--acid)"} />
                <text x={x + 12} y={y + 4} fill="currentColor" fontSize="13">{item.id} {item.name}</text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="panel-inset mt-4 p-4 text-sm">
        <p className="font-semibold">{kit.id} {kit.name}</p>
        <dl className="mt-2 grid gap-1 font-mono text-xs sm:grid-cols-2">
          <div>Bass near a kick: {kit.kickShare.toFixed(2)}</div>
          <div>Quiet / loud: {kit.quietRatio.toFixed(3)}</div>
          <div>Core V01 centroid: {kit.centroidHz} Hz</div>
          <div>{kit.bpm} BPM · {kit.key}</div>
        </dl>
        <p className="mt-2 text-[var(--muted)]">{kit.blurb}</p>
      </div>
    </Section>
  );
}

export function Mindmap() {
  const lab = useLab();
  return (
    <Section id="mindmap">
      <SectionHeading index="03" label="Mindmap" title="The whole collection on one page.">
        Four directions branch from the core. Scroll sideways to see the map. Click a kit to load it in the lab.
      </SectionHeading>
      <div className="mt-8 overflow-x-auto pb-2">
        <div className="flex min-w-[980px] gap-4">
          <div className="w-48 shrink-0 rounded-3xl border border-[var(--acid)] bg-[var(--panel)] p-4">
            <p className="mono text-xs text-[var(--acid)]">CORE</p>
            <p className="mt-2 text-2xl font-semibold">Nostalgia</p>
            <p className="mt-2 text-sm text-[var(--muted)]">192 identities. One tempo and one key per kit.</p>
          </div>
          {directions.map((direction) => (
            <div key={direction} className="w-64 shrink-0 rounded-3xl border border-[var(--line)] bg-[var(--panel)] p-4">
              <h3 className="eyebrow">{direction}</h3>
              <ul className="mt-3 space-y-3">
                {kits.filter((kit) => kit.direction === direction).map((kit) => (
                  <li key={kit.id}>
                    <button type="button" className="text-left" onClick={() => lab.select(kit.id, { scroll: true })}>
                      <span className="mono text-xs text-[var(--muted)]">{kit.id}</span>
                      <span className="mt-1 block text-xl font-semibold">{kit.name}</span>
                      <span className="text-sm text-[var(--muted)]">{kit.bpm} BPM · {kit.key}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <img src="images/mind-map.png" alt="Diagram of Nostalgia: four directions, eight kits, and the ten roles that repeat in each kit." className="mt-6 w-full rounded-3xl border border-[var(--line)]" />
    </Section>
  );
}

export function Harmony() {
  const max = numerals[0].bars;
  return (
    <Section id="harmony">
      <SectionHeading index="04" label="Harmony" title="One function per region, across 512 bars.">
        Eight arrangements, 64 bars each. Numerals are the ones written in the kit index. Bar counts are the lengths of those regions. This is the score, not an audio key detector.
      </SectionHeading>
      <ul className="mt-8 space-y-3">
        {numerals.map((item) => (
          <li key={item.symbol}>
            <div className="flex items-baseline justify-between text-sm">
              <span><span className="mono text-[var(--amber)]">{item.symbol}</span> {item.name}</span>
              <span className="mono">{item.bars} bars</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-[var(--line)]">
              <div className="h-2 rounded-full bg-[var(--acid)]" style={{ width: `${(item.bars / max) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-[var(--muted)]">Scales by bar: natural minor 436, dorian 64, phrygian 12.</p>
    </Section>
  );
}

export function Sound() {
  return (
    <Section id="sound">
      <SectionHeading index="05" label="Sound" title="The MIDI is the notes." highlight="The WAV is the voice.">
        Acid glide and accent live in the synthesizer. The acid MIDI is the note list plus velocity. Overlapping notes are not how this project represents a slide. Core Break V03 is an audio slice edit. Its MIDI is symbolic.
      </SectionHeading>
      <ul className="mt-8 grid gap-3 sm:grid-cols-2">
        {roles.map((role, index) => (
          <li key={role} className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm">
            <span className="mono text-[var(--amber)]">{String(index + 1).padStart(2, "0")}</span>
            <span className="ml-3">{role}</span>
          </li>
        ))}
      </ul>
      <img src="images/signal-flow.png" alt="Signal path from the written kit, through the Python renderer, to WAV, MIDI, and the validator." className="mt-8 w-full rounded-3xl border border-[var(--line)]" />
    </Section>
  );
}

export function Pipeline() {
  return (
    <Section id="pipeline">
      <SectionHeading index="06" label="Pipeline" title="From a written kit to a reopened file.">
        The score is Python. NumPy and SciPy render the audio. The validator reopens the files named in the delivery manifest. A SuperCollider sketch is in the repository and was not executed.
      </SectionHeading>
      <ol className="mt-8 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {pipeline.map(([n, title, where, body]) => (
          <li key={n} className="rounded-3xl border border-[var(--line)] bg-[var(--panel)] p-4">
            <p className="mono text-xs text-[var(--acid)]">{n}</p>
            <h3 className="mt-2 text-2xl font-semibold">{title}</h3>
            <p className="mono mt-1 text-xs text-[var(--amber)]">{where}</p>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{body}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

type Report = { errors?: unknown[]; notes?: string[] };

export function Validation() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    fetch("data/validation-report.json")
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.json() as Promise<Report>;
      })
      .then((data) => { if (live) setReport(data); })
      .catch((reason: unknown) => { if (live) setError(reason instanceof Error ? reason.message : "failed"); });
    return () => { live = false; };
  }, []);
  const notes = report?.notes ?? [];
  const errors = report?.errors?.length ?? 0;
  return (
    <Section id="validation">
      <SectionHeading index="07" label="Validation" title="Checks that actually ran, with their limits stated.">
        This panel reads data/validation-report.json. Nothing here is a projected result, and nothing here is a listening note.
      </SectionHeading>
      {error && (
        <p role="alert" className="mt-6 rounded-lg border border-[var(--amber)] px-4 py-3 text-sm">
          The validation report did not load ({error}). The checks below are the same ten that the report records.
        </p>
      )}
      <p className="mt-8 text-6xl font-semibold">{errors} errors</p>
      <p className="text-[var(--muted)]">{notes.length || 9} notes. Eight are stem-sum residuals. One is K01’s shared trim of 0.485.</p>
      {notes.length > 0 && (
        <ul className="mono mt-4 space-y-1 text-xs text-[var(--muted)]">
          {notes.map((note) => <li key={note}>{note}</li>)}
        </ul>
      )}
      <ol className="mt-6 space-y-3">
        {checks.map(([title, body]) => (
          <li key={title} className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
            <p className="mono text-xs text-[var(--amber)]">{title}</p>
            <p className="mt-1 text-sm leading-6">{body}</p>
          </li>
        ))}
      </ol>
      <h3 className="mt-8 text-xl font-semibold">Limitations</h3>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[var(--muted)]">
        <li>True-peak was not measured. There is no oversampling meter.</li>
        <li>Integrated loudness was not measured. RMS in the review is not LUFS.</li>
        <li>Listening was not part of the check. Rendering is not listening.</li>
        <li>The files were not imported into a commercial DAW in the environment that rendered them.</li>
        <li>The browser plays 8-second excerpts. It does not stream the 64-bar stems.</li>
      </ul>
    </Section>
  );
}

export function Drop() {
  return (
    <Section id="drop">
      <div className="rounded-3xl bg-[var(--ink)] px-6 py-10 text-[var(--bg)] sm:px-10">
        <p className="eyebrow text-[var(--amber)]">08 · Download</p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight">Take the excerpts into your session.</h2>
        <p className="mt-3 max-w-2xl opacity-80">
          The ZIP holds the eight preview files, the captioned commercial, and a manifest. It is not the 3.4 GB stem set. MIDI for every kit is in the repository under public/midi/.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <a className="rounded-full bg-[var(--acid)] px-5 py-3 text-center text-sm font-semibold text-[var(--bg)]" href="nostalgia-excerpts.zip" download>Download the excerpt ZIP</a>
          <a className="rounded-full border border-current px-5 py-3 text-center text-sm font-semibold" href={REPO}>Read the source</a>
        </div>
      </div>
    </Section>
  );
}

export function Brief() {
  const items = [
    ["01", "What it is", "Eight original breakbeat kits, this browser lab, and the Python renderer and validator behind them."],
    ["02", "Who it is for", "Producers who want a break with a paper trail: tempo, key, MIDI fidelity, and a demo that is not pretending to be a master."],
    ["03", "Why it is specific", "Slice edits are labeled when MIDI cannot recreate them. Stems sum to the demo. The validator reopened the files."],
    ["04", "How it is structured", "A Python score renders WAV and MIDI. A static Vite site reads the excerpt files at runtime."],
    ["05", "How people find it", "Search for original breakbeat construction kits, the long-read article, and GitHub topics."],
    ["06", "How people use it", "Audition a kit, compare the map, read the harmony regions, then download the excerpt or the MIDI."],
    ["07", "How people leave with files", "The excerpt ZIP and individual clips have no sign-up. The full stem set is not in this repo."],
    ["08", "How it makes money", "It does not, in this release. A license for the kits is the pattern license: use them in your own music, do not resell the files as a pack."],
    ["09", "How it launches", "GitHub Pages, the article, and the repository. No analytics are wired."],
    ["10", "How it could grow", "DAW import notes, loudness measurement, and hosting for the 24-bit stems once a place for 3.4 GB exists."],
  ];
  return (
    <Section id="brief">
      <SectionHeading index="09" label="Brief" title="The short view: what this is.">
        Ten points, the same shape as a product brief. No cookies and no analytics are loaded by this page.
      </SectionHeading>
      <ol className="mt-8 grid gap-3 md:grid-cols-2">
        {items.map(([n, title, body]) => (
          <li key={n} className="rounded-3xl border border-[var(--line)] bg-[var(--panel)] p-4">
            <p className="mono text-xs text-[var(--amber)]">{n}</p>
            <h3 className="mt-2 text-xl font-semibold">{title}</h3>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{body}</p>
          </li>
        ))}
      </ol>
      <p className="mt-6 text-sm text-[var(--muted)]">This site sets no cookies and loads no analytics. A privacy notice is not required for measurement that does not exist.</p>
    </Section>
  );
}

export function LongRead() {
  return (
    <Section id="article-teaser">
      <SectionHeading index="10" label="Long read" title="The clock and the break live in the same file.">
        The article walks through integer tempo, what an original break means here, and why Core Break V03 MIDI is symbolic. It does not claim anyone listened.
      </SectionHeading>
      <a href="article.html" className="panel mt-8 block p-6 hover:border-[var(--acid)]">
        <p className="eyebrow">Technical readers</p>
        <h3 className="mt-2 text-2xl font-semibold">Nostalgia keeps the break and the clock in the same file</h3>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
          How the kits encode tempo, derive breaks, export stems, and check the files they actually wrote.
        </p>
        <p className="mt-4 text-sm font-semibold text-[var(--acid)]">Read the article</p>
      </a>
    </Section>
  );
}
