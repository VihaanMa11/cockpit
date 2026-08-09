function formatTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour12: false });
}

export default function EventLog({ events }) {
  return (
    <section className="event-log">
      <h2 className="event-log__title">Event log</h2>
      <ul className="event-log__list">
        {events.length === 0 && <li className="event-log__empty">No events yet.</li>}
        {events.map((ev) => (
          <li key={`${ev.ts}-${ev.message}`} className="event-log__item">
            <span className="event-log__time">{formatTime(ev.ts)}</span>
            <span className="event-log__message">{ev.message}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
