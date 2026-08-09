async function post(path) {
  try {
    await fetch(path, { method: "POST" });
  } catch (err) {
    console.error(`DevControls: ${path} failed`, err);
  }
}

export default function DevControls() {
  return (
    <section className="dev-controls">
      <h2 className="dev-controls__title">Dev controls (mock mode — no hardware)</h2>
      <div className="dev-controls__row">
        <button onClick={() => post("/api/dev/rotate/ccw")}>◀ Rotate</button>
        <button onClick={() => post("/api/dev/rotate/cw")}>Rotate ▶</button>
        <button onClick={() => post("/api/dev/press/1")}>RUN</button>
        <button onClick={() => post("/api/dev/press/2")}>Approve</button>
        <button onClick={() => post("/api/dev/press/3")}>Stop</button>
        <button onClick={() => post("/api/dev/press/4")}>NEXT</button>
      </div>
    </section>
  );
}
