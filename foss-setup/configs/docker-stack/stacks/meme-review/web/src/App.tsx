import React from "react";
import { useStore } from "./store";
import { PhoneChrome } from "./components/PhoneFrame";
import { TabBar } from "./components/TabBar";
import { AchievementPopup } from "./components/AchievementPopup";

import { Login } from "./screens/Login";
import { Inbox } from "./screens/Inbox";
import { Compose } from "./screens/Compose";
import { Review } from "./screens/Review";
import { Summary } from "./screens/Summary";
import { Sender } from "./screens/Sender";
import { History } from "./screens/History";
import { Stats } from "./screens/Stats";
import { Achievements } from "./screens/Achievements";
import { Settings } from "./screens/Settings";
import { Activity } from "./screens/Activity";

const TAB_SCREENS = new Set(["inbox", "history", "stats", "achievements"]);

export function App() {
  const { me, loading, route } = useStore();

  let screen: React.ReactNode = null;
  if (loading) {
    screen = <Splash />;
  } else if (!me) {
    screen = <Login />;
  } else {
    switch (route.name) {
      case "inbox":
        screen = <Inbox />;
        break;
      case "compose":
        screen = <Compose />;
        break;
      case "review":
        screen =
          route.sub === "all" ? (
            <Sender slug={route.slug!} />
          ) : route.sub === "summary" ? (
            <Summary slug={route.slug!} />
          ) : (
            <Review slug={route.slug!} />
          );
        break;
      case "history":
        screen = <History />;
        break;
      case "stats":
        screen = <Stats />;
        break;
      case "achievements":
        screen = <Achievements />;
        break;
      case "settings":
        screen = <Settings />;
        break;
      case "activity":
        screen = <Activity />;
        break;
      default:
        screen = <Inbox />;
    }
  }

  const showTabs = !!me && !loading && TAB_SCREENS.has(route.name);

  return (
    <div className="stage">
      <div className="phone">
        <PhoneChrome />
        <div className="screen">{screen}</div>
        {showTabs && <TabBar />}
        <AchievementPopup />
      </div>
    </div>
  );
}

function Splash() {
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "var(--color-neutral-600)",
        fontSize: 30,
      }}
    >
      <i className="ph ph-stack" />
    </div>
  );
}
