export default function ScreenTabs({ screens, activeIndex }) {
  return (
    <nav className="screen-tabs">
      {screens.map((screen, i) => (
        <div key={screen.name} className={`screen-tabs__tab ${i === activeIndex ? "is-active" : ""}`}>
          {screen.name}
        </div>
      ))}
    </nav>
  );
}
