import { useEffect, useState } from "react";
import StatusBar from "./components/StatusBar";
import ScreenTabs from "./components/ScreenTabs";
import WorkflowList from "./components/WorkflowList";
import ActionRow from "./components/ActionRow";
import EventLog from "./components/EventLog";
import DevControls from "./components/DevControls";
import useCockpitSocket from "./hooks/useCockpitSocket";

export default function App() {
  const [config, setConfig] = useState(null);
  const [configError, setConfigError] = useState(null);
  const { state, connected } = useCockpitSocket();

  useEffect(() => {
    fetch("/api/config")
      .then((res) => {
        if (!res.ok) throw new Error(`GET /api/config -> ${res.status}`);
        return res.json();
      })
      .then(setConfig)
      .catch((err) => setConfigError(err.message));
  }, []);

  if (configError) {
    return <div className="app app--loading">Failed to load config: {configError}</div>;
  }

  if (!config || !state) {
    return <div className="app app--loading">Connecting to Cockpit…</div>;
  }

  const activeScreen = config.screens[state.screen_index] ?? config.screens[0];

  return (
    <div className="app">
      <StatusBar connected={connected} mode={state.mode} />
      <ScreenTabs screens={config.screens} activeIndex={state.screen_index} />
      <main className="app__main">
        <WorkflowList
          workflows={activeScreen.workflows}
          selectedIndex={state.selection_index}
          lastAction={state.last_action}
        />
      </main>
      <ActionRow buttonsConfig={config.buttons} buttonsState={state.buttons} />
      <EventLog events={state.events} />
      {state.mode === "mock" && <DevControls />}
    </div>
  );
}
