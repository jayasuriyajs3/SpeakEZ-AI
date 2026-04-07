import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export function ProgressAnalytics() {
  const [sessions, setSessions] = useState<Array<any>>([]);

  useEffect(() => {
    fetch("http://localhost:8000/api/sessions")
      .then((r) => r.json())
      .then(setSessions)
      .catch(() => setSessions([]));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Progress Analytics</h2>
        <p className="mt-1 text-sm text-muted-foreground">Your session history and trend tracking.</p>
      </div>

      <div className="rounded-2xl border border-border/60 bg-card p-6">
        <div className="text-sm font-medium">Recent sessions</div>
        <div className="mt-4 divide-y divide-border/60">
          {sessions.length ? (
            sessions.map((s) => (
              <div key={s.id} className="flex items-center justify-between gap-4 py-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium">Session #{s.id}</div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {new Date(s.started_at).toLocaleString()} • {s.language}
                  </div>
                </div>
                <Link
                  to={`/report/${s.id}`}
                  className="shrink-0 rounded-xl border border-border/60 px-4 py-2 text-sm font-medium hover:bg-muted/60"
                >
                  View report
                </Link>
              </div>
            ))
          ) : (
            <div className="py-6 text-sm text-muted-foreground">No sessions yet. Run a live session and stop it to save.</div>
          )}
        </div>
      </div>
    </div>
  );
}

