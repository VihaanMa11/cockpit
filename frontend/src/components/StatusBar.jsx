export default function StatusBar({ connected, mode }) {
  return (
    <header className="status-bar">
      <span className="status-bar__title">COCKPIT</span>
      <div className="status-bar__right">
        <span className={`badge ${mode === "real" ? "badge--real" : "badge--mock"}`}>
          {mode === "real" ? "REAL" : "MOCK"}
        </span>
        <span className={`badge ${connected ? "badge--live" : "badge--offline"}`}>
          <span className="dot" />
          {connected ? "LIVE" : "OFFLINE"}
        </span>
      </div>
    </header>
  );
}
