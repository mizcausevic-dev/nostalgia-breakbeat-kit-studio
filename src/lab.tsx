import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { kits, type Kit } from "@/data";

type LabValue = {
  index: number;
  kit: Kit;
  playing: boolean;
  query: string;
  direction: string;
  visible: Kit[];
  audioRef: RefObject<HTMLAudioElement | null>;
  setQuery: (value: string) => void;
  setDirection: (value: string) => void;
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
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const kit = kits[index];

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return kits.filter((item) => {
      if (direction !== "all" && item.direction !== direction) return false;
      if (!q) return true;
      return [item.id, item.name, item.direction, item.key, item.region, String(item.bpm)].join(" ").toLowerCase().includes(q);
    });
  }, [query, direction]);

  function select(id: string, options?: { scroll?: boolean }) {
    const next = kits.findIndex((item) => item.id === id);
    if (next < 0) return;
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
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      try {
        await audio.play();
      } catch {
        setPlaying(false);
      }
    } else {
      audio.pause();
    }
  }

  function play(id: string) {
    const next = kits.findIndex((item) => item.id === id);
    if (next < 0) return;
    const audio = audioRef.current;
    if (next === index && audio && !audio.paused) {
      audio.pause();
      return;
    }
    if (next !== index) {
      setIndex(next);
      setPlaying(false);
      setArmed(true);
      return;
    }
    void toggle();
  }

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
    setQuery,
    setDirection,
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
