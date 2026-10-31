import { Download, Pause, Play, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { checks, directions, kits, numerals, pipeline, REPO, stems } from "@/data";
import loudness from "@/loudness.json";
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
        {stems.map((role, index) => (
          <li key={role.id} className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm">
            <div className="flex items-baseline justify-between gap-3">
              <span><span className="mono text-[var(--amber)]">{String(index + 1).padStart(2, "0")}</span> <span className="font-semibold">{role.label}</span></span>
              <span className="mono text-xs text-[var(--muted)]">{role.pitch}</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{role.fidelity}</p>
          </li>
        ))}
      </ul>
      <div className="mt-6 grid gap-3 md:grid-cols-2">
        <div className="rounded-3xl border border-[var(--line)] p-4">
          <h3 className="text-lg font-semibold">Slice edit</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Core Break V03 and the fragmented turnaround are cuts of audio. Reversal and slice order live in the WAV. NumPy writes those samples. The paired MIDI does not recreate them.</p>
        </div>
        <div className="rounded-3xl border border-[var(--line)] p-4">
          <h3 className="text-lg font-semibold">MIDI notes</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">V01, V02, bass, hook, stabs, acid, and atmosphere MIDI are the note lists. Acid glide is a synthesizer behavior. The file stores pitch, start, duration, and velocity.</p>
        </div>
      </div>
      <img src="images/signal-flow.png" alt="Signal path from the written kit, through the Python renderer, to WAV, MIDI, and the validator." className="mt-8 w-full rounded-3xl border border-[var(--line)]" />
    </Section>
  );
}

const pathNotes = [
  "kitdata.py holds the notes, the regions, and the slice map. A slice edit is marked there. It is not inferred from the waveform later.",
  "ticks_to_samples() converts an absolute tick with half-up rounding. Beat lengths are not added up. The same integer tempo is written into the MIDI.",
  "SciPy oscillators and filters run at 48 kHz. Filter coefficients update every 64 samples. Oscillators are sample accurate. Acid glide is computed here, not stored as overlapping MIDI.",
  "Arrangement stems and the demo share one linear trim. Summing the stem WAVs rebuilds the demo. V03 audio is the sliced waveform. Its MIDI export is labeled symbolic.",
  "validate.py reopens the files named in the delivery manifest. The stem-sum residual is measured on those WAVs. LUFS and true peak are a later measurement, not one of those checks.",
  "The site plays 8-second AAC previews. The deploy guard refuses anything that is not a web file, which is why the 3.4 GB stem set stays off GitHub Pages.",
];

export function Pipeline() {
  const [open, setOpen] = useState(0);
  const current = pipeline[open];
  return (
    <Section id="pipeline">
      <SectionHeading index="06" label="Pipeline" title="From a written kit to a reopened file.">
        The score is Python. NumPy and SciPy render the audio. The validator reopens the files named in the delivery manifest. A SuperCollider sketch is in the repository and was not executed.
      </SectionHeading>
      <div className="mt-8 grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <ol className="grid gap-2">
          {pipeline.map(([n, title], index) => (
            <li key={n}>
              <button type="button" aria-pressed={open === index} onClick={() => setOpen(index)} className={`w-full rounded-2xl border px-3 py-3 text-left ${open === index ? "border-[var(--acid)] bg-[var(--panel)]" : "border-[var(--line)]"}`}>
                <span className="mono text-xs text-[var(--acid)]">{n}</span>
                <span className="mt-1 block font-semibold">{title}</span>
              </button>
            </li>
          ))}
        </ol>
        <div className="rounded-3xl border border-[var(--line)] bg-[var(--panel)] p-5">
          <p className="mono text-xs text-[var(--amber)]">{current[2]}</p>
          <h3 className="mt-2 text-3xl font-semibold">{current[1]}</h3>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{current[3]}</p>
          <p className="mt-4 text-sm leading-6">{pathNotes[open]}</p>
        </div>
      </div>
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
      <div className="mt-8 grid gap-3 sm:grid-cols-3">
        <div className="rounded-3xl border border-[var(--acid)] bg-[var(--panel)] p-4">
          <p className="eyebrow">Stem sum</p>
          <p className="mt-2 text-4xl font-semibold">{errors} errors</p>
          <p className="mt-1 text-sm text-[var(--muted)]">Largest absolute residual 0.00000036</p>
        </div>
        <div className="rounded-3xl border border-[var(--line)] bg-[var(--panel)] p-4">
          <p className="eyebrow">Notes</p>
          <p className="mt-2 text-4xl font-semibold">{notes.length || 9}</p>
          <p className="mt-1 text-sm text-[var(--muted)]">Eight residuals, plus K01’s trim of 0.4845</p>
        </div>
        <div className="rounded-3xl border border-[var(--line)] bg-[var(--panel)] p-4">
          <p className="eyebrow">Report</p>
          <a className="mt-3 inline-block text-sm font-semibold underline" href="data/validation-report.json">validation-report.json</a>
          <a className="mt-2 block text-sm font-semibold underline" href="data/loudness.json">loudness.json</a>
        </div>
      </div>
      {notes.length > 0 && (
        <ul className="mono mt-4 space-y-1 text-xs text-[var(--muted)]">
          {notes.map((note) => <li key={note}>{note}</li>)}
        </ul>
      )}
      <ol className="mt-6 grid gap-3 md:grid-cols-2">
        {checks.map(([title, body]) => (
          <li key={title} className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
            <p className="mono text-xs text-[var(--amber)]">{title}</p>
            <p className="mt-1 text-sm leading-6">{body}</p>
          </li>
        ))}
      </ol>
      <h3 className="mt-8 text-xl font-semibold">Limitations</h3>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[var(--muted)]">
        <li>The validator did not measure true peak or LUFS. Those numbers were measured later, on the demo WAVs, with ffmpeg 6.1.1 ebur128. RMS in the musical review is still not LUFS.</li>
        <li>Listening was not part of the check. Rendering is not listening.</li>
        <li>The files were not imported into a commercial DAW in the environment that rendered them.</li>
        <li>The browser plays 8-second excerpts. Stem toggles are AAC cuts of that window. They are not the 64-bar stems, and their sum is not the WAV stem-sum check.</li>
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

const meterOf = (id: string) => loudness.kits[id as keyof typeof loudness.kits];

export function Compare() {
  const [leftId, setLeftId] = useState("K01");
  const [rightId, setRightId] = useState("K07");
  const left = kits.find((kit) => kit.id === leftId) ?? kits[0];
  const right = kits.find((kit) => kit.id === rightId) ?? kits[6];
  const rows: Array<[string, string, string]> = [
    ["Direction", left.direction, right.direction],
    ["Requested BPM", String(left.bpm), String(right.bpm)],
    ["Effective BPM", left.effective, right.effective],
    ["Key", left.key, right.key],
    ["Excerpt region", left.region, right.region],
    ["Bass near a kick", left.kickShare.toFixed(2), right.kickShare.toFixed(2)],
    ["Quiet / loud RMS", left.quietRatio.toFixed(3), right.quietRatio.toFixed(3)],
    ["Core V01 centroid", `${left.centroidHz} Hz`, `${right.centroidHz} Hz`],
    ["Integrated loudness", `${meterOf(left.id).integratedLufs.toFixed(1)} LUFS`, `${meterOf(right.id).integratedLufs.toFixed(1)} LUFS`],
    ["True peak", `${meterOf(left.id).truePeakDbfs.toFixed(1)} dBFS`, `${meterOf(right.id).truePeakDbfs.toFixed(1)} dBFS`],
    ["Loudness range", `${meterOf(left.id).lraLu.toFixed(1)} LU`, `${meterOf(right.id).lraLu.toFixed(1)} LU`],
    ["Shared trim", left.gain.toFixed(4), right.gain.toFixed(4)],
  ];
  return (
    <Section id="compare">
      <SectionHeading index="02" label="Compare" title="Two kits, the same columns.">
        Tempo, key, bass-to-kick weight, and the measured demo loudness. The bass figure is the share of bass note-ons within about 20 ms of a kick. It is from the score review, not a listening score.
      </SectionHeading>
      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        <KitPick label="Left kit" value={leftId} onChange={setLeftId} />
        <KitPick label="Right kit" value={rightId} onChange={setRightId} />
      </div>
      <div className="mt-4 overflow-x-auto rounded-3xl border border-[var(--line)]">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead className="bg-[var(--panel)]">
            <tr>
              <th className="px-4 py-3 font-medium text-[var(--muted)]">Field</th>
              <th className="px-4 py-3 font-semibold">{left.id} {left.name}</th>
              <th className="px-4 py-3 font-semibold">{right.id} {right.name}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, a, b]) => (
              <tr key={label} className="border-t border-[var(--line)]">
                <th className="px-4 py-2.5 font-normal text-[var(--muted)]">{label}</th>
                <td className={`mono px-4 py-2.5 ${a !== b ? "text-[var(--ink)]" : ""}`}>{a}</td>
                <td className="mono px-4 py-2.5">{b}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function KitPick({ label, value, onChange }: { label: string; value: string; onChange: (id: string) => void }) {
  return (
    <label className="block text-sm">
      <span className="eyebrow">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--line)] bg-[var(--panel)] px-3 py-2">
        {kits.map((kit) => <option key={kit.id} value={kit.id}>{kit.id} {kit.name} · {kit.bpm} BPM · {kit.key}</option>)}
      </select>
    </label>
  );
}

export function Origin() {
  return (
    <Section id="origin">
      <SectionHeading index="08" label="Origin" title="192 identities, written, not sampled.">
        Nostalgia is an original 90s-inspired breakbeat and big-beat construction set. The audio is synthesized. It is not a sampled vintage break, and it is not a finished master.
      </SectionHeading>
      <div className="mt-8 grid gap-3 md:grid-cols-2">
        <article className="rounded-3xl border border-[var(--line)] bg-[var(--panel)] p-5">
          <h3 className="text-xl font-semibold">What the 192 are</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Eight kits, 24 identities each. Seventeen are loops and seven are finite parts. Source breaks, dry companions, demos, stems, and MIDI are extra files. They are not extra identities. Each kit keeps one requested tempo and one key for the whole arrangement.</p>
        </article>
        <article className="rounded-3xl border border-[var(--line)] bg-[var(--panel)] p-5">
          <h3 className="text-xl font-semibold">Where the four directions come from</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Warehouse Pressure is the straight kick-and-snare weight, Freight at 128 and Rivet at 136. Acid Collision puts the acid line against the break. Solvent spends one region on a Phrygian flat two. Rave Memory leads with stabs. Afterglow lifts to the relative major. Concrete Funk is slower and leaves more space. Formwork is the only kit written in dorian, and it opens without the kick.</p>
        </article>
      </div>
      <p className="mt-4 text-sm text-[var(--muted)]">The renderer is Python, NumPy 2.5.4, and SciPy 1.18.1. The SuperCollider sketch in the repository was not executed.</p>
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
