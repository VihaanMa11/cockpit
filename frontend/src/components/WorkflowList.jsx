export default function WorkflowList({ workflows, selectedIndex, lastAction }) {
  if (!workflows.length) {
    return <div className="workflow-list workflow-list--empty">No workflows configured on this screen.</div>;
  }

  return (
    <ul className="workflow-list">
      {workflows.map((wf, i) => {
        const isSelected = i === selectedIndex;
        const isTarget = lastAction?.type === "launch" && lastAction.label === wf.label;
        const statusClass = isTarget ? `workflow-list__row--${lastAction.status}` : "";
        return (
          <li
            key={wf.label}
            className={`workflow-list__row ${isSelected ? "is-selected" : ""} ${statusClass}`}
          >
            <span className="workflow-list__marker">{isSelected ? "▶" : ""}</span>
            <span className="workflow-list__label">{wf.label}</span>
            {isTarget && (
              <span className="workflow-list__status">
                {lastAction.status === "pending" && "▶ launching…"}
                {lastAction.status === "ok" && "✓ done"}
                {lastAction.status === "failed" && "✗ failed"}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
