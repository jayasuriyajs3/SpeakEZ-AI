import { Routes, Route, Navigate } from "react-router-dom";
import { Landing } from "@/pages/Landing";
import { Dashboard } from "@/pages/Dashboard";
import { SessionReport } from "@/pages/SessionReport";
import { ProgressAnalytics } from "@/pages/ProgressAnalytics";
import { Interview } from "@/pages/Interview";
import { AppShell } from "@/components/shell/AppShell";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/interview" element={<Interview />} />
        <Route path="/report/:sessionId" element={<SessionReport />} />
        <Route path="/analytics" element={<ProgressAnalytics />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

