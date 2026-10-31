import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { kits, stems, type Kit } from "@/data";

export type Audition = "demo" | "stems";

type LabValue = {
  index: number;
  kit: Kit;
  playing: boolean;
  query: string;
  direction: string;
  visible: Kit[];
  audioRef: RefObject<HTMLAudioElement | null>;
  audition: Audition;
  off: string[];
  stemState: "idle" | "loading" | "ready" | "error";
  setQuery: (value: string) => void;
  setDirection: (value: string) => void;
  setAudition: (mode: Audition) => void;
  toggleStem: (id: string) => void;
  soloStem: (id: string) => void;
  resetStems: () => void;
  select: (id: string, options?: { scroll?: boolean }) => void;
  step: (delta: number) => void;
  toggle: () => Promise<void>;
  play: (id: string) => void;
  mark: (next: boolean) => void;
  armed: boolean;
  clearArmed: () => void;
  resetFilters: () => void;
};

const LabContext = createContext<LabValue | null>(null);

const SPACE_ROLES = new Set(["button", "switch", "checkbox", "menuitem", "option", "tab", "radio", "link"]);
const ARROW_ROLES = new Set(["slider", "radio", "tab", "menuitem", "option", "combobox", "spinbutton", "textbox"]);

function ignoreKey(event: KeyboardEvent) {
  if (event.metaKey || event.ctrlKey || event.altKey || event.defaultPrevented) return true;
  const el = event.target as HTMLElement | null;
  if (!el || el === document.body) return false;
  if (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName)) return true;
  const role = el.getAttribute("role") ?? (el.tagName === "BUTTON" ? "button" : el.tagName === "A" ? "link" : "");
  return event.key === " " ? SPACE_ROLES.has(role) : ARROW_ROLES.has(role);
}

export function LabProvider({ children }: { children: ReactNode }) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [query, setQuery] = useState("");
  const [direction, setDirection] = useState("all");
  const [armed, setArmed] = useState(false);
  const [audition, setAuditionState] = useState<Audition>("demo");
  const [off, setOff] = useState<string[]>([]);
  const [stemState, setStemState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const buffersRef = useRef<Map<string, AudioBuffer>>(new Map());
  const gainsRef = useRef<Map<string, GainNode>>(new Map());
  const sourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const kit = kits[index];
  const offRef = useRef(off);
  offRef.current = off;

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return kits.filter((item) => {
      if (direction !== "all" && item.direction !== direction) return false;
      if (!q) return true;
      return [item.id, item.name, item.direction, item.key, item.region, String(item.bpm)].join(" ").toLowerCase().includes(q);
    });
  }, [query, direction]);

  function stopStems() {
    for (const source of sourcesRef.current) {
      source.onended = null;
      try { source.stop(); } catch { /* already stopped */ }
    }
    sourcesRef.current = [];
    gainsRef.current.clear();
  }

  function applyGains() {
    const ctx = ctxRef.current;
    if (!ctx) return;
    for (const [id, gain] of gainsRef.current) {
      gain.gain.setValueAtTime(offRef.current.includes(id) ? 0 : 1, ctx.currentTime);
    }
  }

  async function context() {
    if (!ctxRef.current) ctxRef.current = new AudioContext();
    if (ctxRef.current.state === "suspended") await ctxRef.current.resume();
    return ctxRef.current;
  }

  async function loadStems(id: string) {
    const missing = stems.some((stem) => !buffersRef.current.has(`${id}-${stem.id}`));
    if (!missing) {
      setStemState("ready");
      return;
    }
    const ctx = await context();
    setStemState("loading");
    try {
      await Promise.all(stems.map(async (stem) => {
        const key = `${id}-${stem.id}`;
        if (buffersRef.current.has(key)) return;
        const response = await fetch(`audio/stems/${key}.m4a`);
        if (!response.ok) throw new Error(String(response.status));
        const audio = await ctx.decodeAudioData(await response.arrayBuffer());
        buffersRef.current.set(key, audio);
      }));
      setStemState("ready");
    } catch {
      setStemState("error");
      throw new Error("stems");
    }
  }

  function startStems(offset = 0) {
    const ctx = ctxRef.current;
    if (!ctx) return;
    stopStems();
    const when = ctx.currentTime + 0.03;
    let started = 0;
    for (const stem of stems) {
      const buffer = buffersRef.current.get(`${kits[index].id}-${stem.id}`);
      if (!buffer) continue;
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      const gain = ctx.createGain();
      gain.gain.value = offRef.current.includes(stem.id) ? 0 : 1;
      source.connect(gain).connect(ctx.destination);
      const at = Math.min(offset, Math.max(0, buffer.duration - 0.05));
      source.start(when, at);
      sourcesRef.current.push(source);
      gainsRef.current.set(stem.id, gain);
      started += 1;
      source.onended = () => {
        if (sourcesRef.current.includes(source)) setPlaying(false);
      };
    }
    setPlaying(started > 0);
  }

  function pauseDemo() {
    audioRef.current?.pause();
  }

  function select(id: string, options?: { scroll?: boolean }) {
    const next = kits.findIndex((item) => item.id === id);
    if (next < 0) return;
    stopStems();
    pauseDemo();
    setIndex(next);
    setPlaying(false);
    if (options?.scroll) document.getElementById("lab")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function step(delta: number) {
    const pool = visible.length ? visible : kits;
    const at = pool.findIndex((item) => item.id === kits[index].id);
    const next = pool[(at + delta + pool.length) % pool.length];
    select(next.id);
  }

  async function toggle() {
    if (audition === "stems") {
      if (sourcesRef.current.length) {
        stopStems();
        setPlaying(false);
        return;
      }
      try {
        const id = kit.id;
        await loadStems(id);
        if (kits[index].id !== id) return;
        startStems(0);
      } catch {
        setPlaying(false);
      }
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      try { await audio.play(); } catch { setPlaying(false); }
    } else {
      audio.pause();
    }
  }

  function play(id: string) {
    const next = kits.findIndex((item) => item.id === id);
    if (next < 0) return;
    if (next === index && (playing || (audioRef.current && !audioRef.current.paused))) {
      void toggle();
      return;
    }
    if (next !== index) {
      select(id);
      setArmed(true);
      return;
    }
    void toggle();
  }

  function setAudition(mode: Audition) {
    if (mode === audition) return;
    stopStems();
    pauseDemo();
    setPlaying(false);
    setAuditionState(mode);
    if (mode === "stems") void loadStems(kit.id).catch(() => undefined);
  }

  useEffect(() => {
    applyGains();
  }, [off]);

  useEffect(() => {
    if (!armed) return;
    setArmed(false);
    void toggle();
  }, [armed, kit.id]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (ignoreKey(event)) return;
      if (event.key === " ") {
        event.preventDefault();
        void toggle();
      } else if (event.key === "ArrowRight" || event.key.toLowerCase() === "k") {
        event.preventDefault();
        step(1);
      } else if (event.key === "ArrowLeft" || event.key.toLowerCase() === "j") {
        event.preventDefault();
        step(-1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const value: LabValue = {
    index,
    kit,
    playing,
    query,
    direction,
    visible,
    audioRef,
    audition,
    off,
    stemState,
    setQuery,
    setDirection,
    setAudition,
    toggleStem: (id) => setOff((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]),
    soloStem: (id) => setOff(stems.map((stem) => stem.id).filter((item) => item !== id)),
    resetStems: () => setOff([]),
    select,
    step,
    toggle,
    play,
    mark: setPlaying,
    armed,
    clearArmed: () => setArmed(false),
    resetFilters: () => {
      setQuery("");
      setDirection("all");
    },
  };

  return <LabContext.Provider value={value}>{children}</LabContext.Provider>;
}

export function useLab() {
  const value = useContext(LabContext);
  if (!value) throw new Error("useLab must be used inside LabProvider");
  return value;
}
