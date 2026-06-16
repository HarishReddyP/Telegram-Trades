import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview";
import OpenPositions from "./pages/OpenPositions";
import ClosedTrades from "./pages/ClosedTrades";
import DailyPnL from "./pages/DailyPnL";
import StrategyAnalytics from "./pages/StrategyAnalytics";
import AlertsLog from "./pages/AlertsLog";
import Settings from "./pages/Settings";
import RiskControls from "./pages/RiskControls";

const NAV = [
  { to: "/overview", label: "Overview" },
  { to: "/open", label: "Open Positions" },
  { to: "/closed", label: "Closed Trades" },
  { to: "/daily", label: "Daily P&L" },
  { to: "/strategy", label: "Strategy Analytics" },
  { to: "/alerts", label: "Telegram Alerts Log" },
  { to: "/settings", label: "Settings" },
  { to: "/risk", label: "Risk Controls" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-edge bg-panel px-3 py-5">
        <div className="px-2 mb-6">
          <div className="text-sm font-semibold">Trade Alerts</div>
          <div className="text-xs text-muted">paper-trading MVP</div>
        </div>
        <nav className="space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm ${
                  isActive ? "bg-panel2 text-white border border-edge" : "text-muted hover:text-white hover:bg-panel2"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="flex-1 px-6 py-6 max-w-[1400px]">
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<Overview />} />
          <Route path="/open" element={<OpenPositions />} />
          <Route path="/closed" element={<ClosedTrades />} />
          <Route path="/daily" element={<DailyPnL />} />
          <Route path="/strategy" element={<StrategyAnalytics />} />
          <Route path="/alerts" element={<AlertsLog />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/risk" element={<RiskControls />} />
        </Routes>
      </main>
    </div>
  );
}
