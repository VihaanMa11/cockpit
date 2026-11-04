import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useCockpitSocket from "./hooks/useCockpitSocket";

const SCREEN_NAMES = ["Home", "Music", "Agents", "Tasks"];
const pad = (n) => String(n).padStart(2, "0");
const formatTime = (seconds = 0) => {
  const safeSeconds = Number.isFinite(Number(seconds)) ? Math.max(0, Math.floor(Number(seconds))) : 0;
  return `${pad(Math.floor(safeSeconds / 60))}:${pad(safeSeconds % 60)}`;
};

function sendEvent(event) {
  const localKiosk = ["127.0.0.1", "localhost"].includes(window.location.hostname) && window.location.port === "8000";
  const prefix = localKiosk ? "/api/local/event" : "/api/dev/event";
  fetch(`${prefix}/${event}`, { method: "POST" }).catch(() => {});
}

function setScreen(index) {
  const localKiosk = ["127.0.0.1", "localhost"].includes(window.location.hostname) && window.location.port === "8000";
  const prefix = localKiosk ? "/api/local/screen" : "/api/dev/screen";
  fetch(`${prefix}/${index}`, { method: "POST" }).catch(() => {});
}

function selectWorkflow(index) {
  const localKiosk = ["127.0.0.1", "localhost"].includes(window.location.hostname) && window.location.port === "8000";
  const prefix = localKiosk ? "/api/local/select" : "/api/dev/select";
  fetch(`${prefix}/${index}`, { method: "POST" }).catch(() => {});
}

function Hints({ children }) {
  return <footer className="hints">{children}</footer>;
}

function Dots({ active }) {
  return <nav className="dots" aria-label="Cockpit screens">{SCREEN_NAMES.map((name, i) => <button key={name} type="button" className={i === active ? "dot active" : "dot"} aria-label={`Show ${name}`} aria-current={i === active ? "page" : undefined} onClick={() => setScreen(i)} />)}</nav>;
}

function Glyph({ name, size = 20 }) {
  const paths = {
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01"/></>,
    temp: <><path d="M14 14.8V5a4 4 0 0 0-8 0v9.8a6 6 0 1 0 8 0Z"/><path d="M10 11v7"/></>,
    drop: <path d="M12 2.5S5 11 5 15a7 7 0 0 0 14 0c0-4-7-12.5-7-12.5Z"/>,
    cpu: <><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 1v4m6-4v4M9 19v4m6-4v4M1 9h4m-4 6h4m14-6h4m-4 6h4"/><circle cx="12" cy="12" r="2"/></>,
    wifi: <><path d="M2 8a15 15 0 0 1 20 0M5 12a10 10 0 0 1 14 0m-11 4a5 5 0 0 1 8 0"/><circle cx="12" cy="20" r="1" fill="currentColor" stroke="none"/></>,
    mountain: <path d="m2 19 6.5-9 3 4 4.5-8L22 19H2Zm5-2h10l-3-5-2 3-2-2-3 4Z" fill="currentColor" stroke="none"/>,
    previous: <><path d="M6 5v14M19 6 9 12l10 6z" fill="currentColor" stroke="none"/></>,
    next: <><path d="M18 5v14M5 6l10 6-10 6z" fill="currentColor" stroke="none"/></>,
    pause: <><rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/><rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/></>,
    play: <path d="m7 4 13 8-13 8z" fill="currentColor" stroke="none"/>,
    volume: <><path d="M4 9v6h4l5 4V5L8 9H4Z" fill="currentColor" stroke="none"/><path d="M16 9a5 5 0 0 1 0 6m2-9a9 9 0 0 1 0 12"/></>,
    bars: <><rect x="3" y="9" width="3" height="6" rx="1" fill="currentColor" stroke="none"/><rect x="8" y="5" width="3" height="14" rx="1" fill="currentColor" stroke="none"/><rect x="13" y="7" width="3" height="10" rx="1" fill="currentColor" stroke="none"/><rect x="18" y="10" width="3" height="4" rx="1" fill="currentColor" stroke="none"/></>,
  };
  return <svg className={`glyph glyph-${name}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Home({ config, sensors }) {
  const [now, setNow] = useState(new Date());
  const [wallpaperUrl, setWallpaperUrl] = useState(null);
  useEffect(() => { const timer = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(timer); }, []);
  const configuredWallpaper = config.ui?.wallpaper;
  useEffect(() => {
    let active = true;
    if (!configuredWallpaper) { setWallpaperUrl(null); return () => { active = false; }; }
    fetch(configuredWallpaper, { method: "HEAD" })
      .then((response) => { if (active) setWallpaperUrl(response.ok ? configuredWallpaper : null); })
      .catch(() => { if (active) setWallpaperUrl(null); });
    return () => { active = false; };
  }, [configuredWallpaper]);
  const clock = config.ui?.clock_24h === false ? now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : `${pad(now.getHours())}:${pad(now.getMinutes())}`;
  const date = now.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
  const wallpaper = wallpaperUrl;
  const ambient = sensors.temperature?.value;
  const humidity = sensors.humidity?.value;
  return <section className={`screen home ${wallpaper ? "has-wallpaper" : ""}`} style={wallpaper ? { backgroundImage: `linear-gradient(180deg,rgba(3,10,15,.28),rgba(3,10,15,.45)),url("${wallpaper}")` } : undefined}>
    <div className="home-main">
      <div className="clock-block"><div className="clock">{clock}</div><div className="date"><Glyph name="calendar" size={17}/><span>{date}</span></div></div>
      <aside className="ambient-card"><span className="ambient-icon"><Glyph name="drop" size={34}/></span><b>{ambient == null ? "--°" : `${Number(ambient).toFixed(0)}°`}</b><small>{sensors.temperature?.stale ? "TEMP · STALE" : "ROOM TEMP"}</small><div className="ambient-humidity">{humidity == null ? "--" : `${Math.round(humidity)}%`} <small>HUMIDITY</small></div></aside>
    </div>
    <div className="stats">
      <span className="stat lime"><Glyph name="temp" size={26}/><b>{ambient == null ? "--°" : `${Number(ambient).toFixed(0)}°`}</b><small>{sensors.temperature?.stale ? "TEMP · STALE" : "ROOM TEMP"}</small></span>
      <span className="stat cyan"><Glyph name="drop" size={26}/><b>{humidity == null ? "--%" : `${Math.round(humidity)}%`}</b><small>{sensors.humidity?.stale ? "HUMID · STALE" : "HUMIDITY"}</small></span>
      <span className="stat yellow"><Glyph name="cpu" size={26}/><b>{sensors.cpu_temperature == null ? "--°" : `${Math.round(sensors.cpu_temperature)}°`}</b><small>CPU TEMP</small></span>
      <span className={`stat mint ${sensors.wifi_connected ? "connected" : ""}`}><Glyph name="wifi" size={27}/><b>{sensors.wifi_connected == null ? "--" : sensors.wifi_connected ? "ONLINE" : "OFFLINE"}</b><small>NETWORK</small></span>
    </div>
    <div className="home-caption"><span>STAY IN CONTROL</span><Glyph name="mountain" size={22}/></div>
  </section>;
}

function MusicScreen({ music }) {
  const playing = music.status === "playing";
  const [artworkFailed, setArtworkFailed] = useState(false);
  useEffect(() => { setArtworkFailed(false); }, [music.art_url]);
  const discRef = useRef(null);
  const angleRef = useRef(0);
  const frameRef = useRef(null);
  const wasPlayingRef = useRef(false);
  const volumeValueRef = useRef(music.volume ?? 0);
  const lastVolumeTargetRef = useRef(null);
  useEffect(() => { if (music.volume != null) volumeValueRef.current = music.volume; }, [music.volume]);
  useEffect(() => {
    if (frameRef.current) cancelAnimationFrame(frameRef.current);
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (playing && !reduceMotion) {
      wasPlayingRef.current = true;
      let previous = null;
      const spin = (time) => {
        const delta = previous == null ? 0 : Math.min(48, time - previous);
        previous = time;
        angleRef.current = (angleRef.current + delta * 0.09) % 360;
        if (discRef.current) discRef.current.style.transform = `rotate(${angleRef.current}deg)`;
        frameRef.current = requestAnimationFrame(spin);
      };
      frameRef.current = requestAnimationFrame(spin);
    } else if (wasPlayingRef.current && !reduceMotion) {
      const start = performance.now();
      const initial = angleRef.current;
      const easeOut = (time) => {
        const progress = Math.min(1, (time - start) / 700);
        const eased = 1 - Math.pow(1 - progress, 3);
        angleRef.current = initial + 45 * eased;
        if (discRef.current) discRef.current.style.transform = `rotate(${angleRef.current}deg)`;
        if (progress < 1) frameRef.current = requestAnimationFrame(easeOut);
        else { wasPlayingRef.current = false; frameRef.current = null; }
      };
      frameRef.current = requestAnimationFrame(easeOut);
    } else if (reduceMotion) {
      wasPlayingRef.current = false;
    }
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current); };
  }, [playing]);
  const duration = music.duration || 0;
  const elapsed = Math.min(music.elapsed || 0, duration || music.elapsed || 0);
  const pct = duration ? Math.min(100, (elapsed / duration) * 100) : 0;
  const setVolumeAtPointer = (event) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const target = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
    const previous = lastVolumeTargetRef.current ?? volumeValueRef.current;
    const steps = Math.floor(Math.abs(target - previous) / 0.05);
    const direction = target > previous ? "up" : "down";
    for (let step = 0; step < steps; step += 1) sendEvent(direction);
    lastVolumeTargetRef.current = target;
    volumeValueRef.current = target;
  };
  return <section className="screen music-screen">
    <div className="screen-title"><span>MUSIC</span><span className={playing ? "playing-label" : "idle-label"}>{playing ? "PLAYING" : music.active ? "PAUSED" : "NO PLAYER"}</span></div>
    <div className="music-hero">
      <div className={`disc-wrap ${playing ? "is-playing" : ""}`}><div className="record-glow"/><div ref={discRef} className="disc"><div className="disc-art">{music.art_url && !artworkFailed ? <img key={music.art_url} src={music.art_url} alt="Album artwork" decoding="async" onError={() => setArtworkFailed(true)} /> : <div className="generic-art"><Glyph name="mountain" size={34}/><span>{artworkFailed ? "ART UNAVAILABLE" : "COCKPIT"}</span></div>}</div><div className="disc-hole" /></div></div>
      <div className="track-info">
        <div className={`now-playing ${playing ? "live" : ""}`}><Glyph name="bars" size={19}/><span>{playing ? "NOW PLAYING" : music.active ? "ON PAUSE" : "READY WHEN YOU ARE"}</span></div>
        <div className="track-title">{music.active ? music.title : "Nothing playing"}</div>
        <div className="artist">{music.artist || (music.active ? music.album : "Connect a player to begin")}</div>
        {music.active && music.album && music.artist && <div className="album-line"><span className="mini-record">◉</span>{music.album}</div>}
      </div>
    </div>
    <div className="music-progress"><div className="progress"><div style={{ width: `${pct}%` }} /></div><div className="time-row"><span>{formatTime(elapsed)}</span><span>{formatTime(duration)}</span></div></div>
    <div className="music-controls">
      <div className="volume-control"><Glyph name="volume" size={23}/><div className="volume-track" role="slider" tabIndex={0} aria-label="Volume" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round((music.volume ?? 0) * 100)} onPointerDown={(event) => { event.currentTarget.setPointerCapture(event.pointerId); lastVolumeTargetRef.current = null; setVolumeAtPointer(event); }} onPointerMove={(event) => { if (event.buttons) setVolumeAtPointer(event); }} onPointerUp={() => { lastVolumeTargetRef.current = null; }} onKeyDown={(event) => { if (!["ArrowLeft", "ArrowDown", "ArrowRight", "ArrowUp", "Home", "End"].includes(event.key)) return; event.preventDefault(); const current = music.volume ?? volumeValueRef.current; const target = event.key === "Home" ? 0 : event.key === "End" ? 1 : Math.max(0, Math.min(1, current + (["ArrowRight", "ArrowUp"].includes(event.key) ? 0.05 : -0.05))); const steps = Math.round(Math.abs(target - current) / 0.05); for (let step = 0; step < steps; step += 1) sendEvent(target > current ? "up" : "down"); volumeValueRef.current = target; }}><i style={{ width: `${Math.max(0, Math.min(100, (music.volume ?? 0) * 100))}%` }}/><span className="volume-knob" style={{ left: `${Math.max(0, Math.min(100, (music.volume ?? 0) * 100))}%` }}/></div><b>{music.volume == null ? "--%" : `${Math.round(music.volume * 100)}%`}</b></div>
      <div className="transport">
        <button onClick={() => sendEvent("stop")} aria-label="Previous track"><Glyph name="previous" size={24}/></button>
        <button className="primary-transport" onClick={() => sendEvent("run")} aria-label={playing ? "Pause" : "Play"}><Glyph name={playing ? "pause" : "play"} size={28}/></button>
        <button onClick={() => sendEvent("approve")} aria-label="Next track"><Glyph name="next" size={24}/></button>
      </div>
    </div>
  </section>;
}

function Agents({ workflows = [], states = [], selection = 0, onSelect }) {
  const selected = workflows[selection];
  const [wide, setWide] = useState(() => window.innerWidth >= 850);
  useEffect(() => {
    const updateWidth = () => setWide(window.innerWidth >= 850);
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);
  const rows = useMemo(() => {
    const count = wide ? 7 : 4;
    if (!selected) return workflows.slice(0, count).map((workflow, i) => ({ workflow, i }));
    const start = Math.max(0, Math.min(selection - Math.floor(count / 2), workflows.length - count));
    return workflows.slice(start, start + count).map((workflow, offset) => ({ workflow, i: start + offset }));
  }, [workflows, selection, selected, wide]);
  return <section className="screen agents-screen">
    <div className="screen-title"><span>n8n AGENTS</span><span>{workflows.length} FLOWS</span></div>
    <div className="agent-list">{rows.map(({ workflow, i }) => {
      const status = states[i] || { status: "idle" };
      return <button key={`${workflow.label}-${i}`} type="button" className={`agent-row ${i === selection ? "selected" : ""}`} aria-pressed={i === selection} onClick={() => onSelect(i)}>
        <span className={`status-dot ${status.status}`} />
        <div className="agent-copy"><b>{workflow.label}</b><small>{workflow.category || "WORKFLOW"}{workflow.description ? ` · ${workflow.description}` : ""}{status.last_run ? ` · ${new Date(status.last_run * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : ""}</small></div>
        <span className={`agent-state ${status.status}`}>{status.status === "success" ? "OK" : status.status === "failed" ? "FAIL" : status.status === "running" ? "RUN…" : "IDLE"}</span>
      </button>;
    })}{!workflows.length && <div className="empty-list">No workflows configured</div>}</div>
    <Hints><span>◀ / ▶ SCREEN</span><span>↑ / ↓ SELECT</span><button type="button" className="touch-run" onClick={() => sendEvent("approve")} disabled={!selected}>RUN SELECTED</button></Hints>
  </section>;
}

function Tasks({ workflows = [], states = [], selection = 0, onSelect }) {
  const taskWorkflows = useMemo(() => {
    const filtered = workflows.map((wf, i) => ({ ...wf, originalIndex: i })).filter((wf) => wf.category === "Tasks");
    return filtered.length > 0 ? filtered : workflows.map((wf, i) => ({ ...wf, originalIndex: i }));
  }, [workflows]);
  const activeSelection = selection % Math.max(1, taskWorkflows.length);
  const selected = taskWorkflows[activeSelection];
  return (
    <section className="screen agents-screen">
      <div className="screen-title"><span>ACTIVE TASKS</span><span>{taskWorkflows.length} TASKS</span></div>
      <div className="agent-list">
        {taskWorkflows.map((item, idx) => {
          const status = states[item.originalIndex] || { status: "idle" };
          const isSelected = idx === activeSelection;
          return (
            <button key={`task-${item.label}-${idx}`} type="button" className={`agent-row ${isSelected ? "selected" : ""}`} onClick={() => onSelect(item.originalIndex)}>
              <span className={`status-dot ${status.status === "success" ? "success" : "idle"}`} />
              <div className="agent-copy">
                <b>{item.label}</b>
                <small>{status.status === "success" ? "✓ COMPLETED" : "PENDING ACTION"}</small>
              </div>
              <span className={`agent-state ${status.status === "success" ? "success" : "idle"}`}>
                {status.status === "success" ? "DONE" : "TODO"}
              </span>
            </button>
          );
        })}
      </div>
      <Hints><span>◀ / ▶ SCREEN</span><span>↑ / ↓ SCROLL</span><button type="button" className="touch-run" onClick={() => sendEvent("run")}>MARK DONE / RUN</button></Hints>
    </section>
  );
}

export default function App() {
  const [config, setConfig] = useState(null);
  const { state, connected } = useCockpitSocket();
  useEffect(() => { fetch("/api/config").then((r) => r.json()).then(setConfig).catch(() => {}); }, []);
  const screen = state?.screen_index || 0;
  const input = useCallback((event) => sendEvent(event), []);
  useEffect(() => {
    const held = new Map();
    const onDown = (e) => {
      const event = ({ ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down", Enter: "run", a: "approve", A: "approve", s: "stop", S: "stop", v: "voice", V: "voice" })[e.key];
      if (!event) return;
      e.preventDefault();
      if (held.has(e.key)) return;
      input(event);
      const timer = screen === 1 && (event === "up" || event === "down") ? setInterval(() => input(event), 180) : null;
      held.set(e.key, timer);
    };
    const onUp = (e) => { clearInterval(held.get(e.key)); held.delete(e.key); };
    const onBlur = () => { held.forEach(clearInterval); held.clear(); };
    window.addEventListener("keydown", onDown); window.addEventListener("keyup", onUp);
    window.addEventListener("blur", onBlur);
    return () => { window.removeEventListener("keydown", onDown); window.removeEventListener("keyup", onUp); window.removeEventListener("blur", onBlur); onBlur(); };
  }, [input, screen]);
  if (!config || !state) return <main className="loading">COCKPIT <span>CONNECTING…</span></main>;
  const workflows = state?.workflows_list || config.workflows || [];
  return <main className="console">
    <div className="topline"><span className="brand"><i className="brand-mark"><b /><b /><b /></i><span>COCKPIT<small>DESK CONSOLE</small></span></span><span className={`connection ${connected ? "" : "off"}`}><i />{state.mode?.toUpperCase()} <b>·</b> {connected ? "LIVE" : "OFFLINE"}</span></div>
    <div className="viewport" key={screen}>
      {screen === 0 && <Home config={config} sensors={state.sensors || {}} />}
      {screen === 1 && <MusicScreen music={state.music || {}} />}
      {screen === 2 && <Agents workflows={workflows} states={state.workflows} selection={state.selection_index || 0} onSelect={selectWorkflow} />}
      {screen === 3 && <Tasks workflows={workflows} states={state.workflows} selection={state.selection_index || 0} onSelect={selectWorkflow} />}
    </div>
    <Dots active={screen} />
  </main>;
}

