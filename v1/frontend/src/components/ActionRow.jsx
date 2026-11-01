const ORDER = [
  { id: "1", fallback: "RUN" },
  { id: "2", fallback: "Approve" },
  { id: "3", fallback: "Stop" },
  { id: "4", fallback: "NEXT" },
];

export default function ActionRow({ buttonsConfig, buttonsState }) {
  return (
    <div className="action-row">
      {ORDER.map(({ id, fallback }) => (
        <div key={id} className={`action-row__indicator ${buttonsState[id] ? "is-active" : ""}`}>
          {buttonsConfig[id]?.label ?? fallback}
        </div>
      ))}
    </div>
  );
}
