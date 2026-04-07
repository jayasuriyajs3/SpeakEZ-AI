import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function SessionReport() {
  const { sessionId } = useParams();
  const [data, setData] = useState<any>(null);

  const apiUrl = useMemo(() => `http://localhost:8000/api/sessions/${sessionId}`, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    fetch(apiUrl)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, [apiUrl, sessionId]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Session Report</h2>
        <p className="mt-1 text-sm text-muted-foreground">Session ID: {sessionId}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-border/60 bg-card p-6 md:col-span-2">
          <div className="text-sm font-medium">Transcript</div>
          <div className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">
            {data?.transcript ? data.transcript : "No transcript yet. End a live session to generate a report."}
          </div>
        </div>
        <div className="rounded-2xl border border-border/60 bg-card p-6">
          <div className="text-sm font-medium">Export</div>
          <p className="mt-2 text-sm text-muted-foreground">Download a PDF report for sharing.</p>
          <a
            className="mt-4 inline-block rounded-xl bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
            href={`http://localhost:8000/api/sessions/${sessionId}/report.pdf`}
            target="_blank"
            rel="noreferrer"
          >
            Export PDF
          </a>
        </div>
      </div>

      <div className="rounded-2xl border border-border/60 bg-card p-6">
        <div className="text-sm font-medium">Session timeline</div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Chart title="WPM" data={data?.metrics ?? []} dataKey="wpm" domain={undefined} />
          <Chart title="Confidence" data={data?.metrics ?? []} dataKey="confidence" domain={[0, 100]} />
        </div>
      </div>
    </div>
  );
}

function Chart({
  title,
  data,
  dataKey,
  domain
}: {
  title: string;
  data: any[];
  dataKey: string;
  domain?: any;
}) {
  const series = (data ?? []).map((p) => ({ t: (p.t_ms ?? 0) / 1000, v: p[dataKey] ?? 0 }));
  return (
    <div className="h-44 rounded-xl border border-border/60 bg-muted/20 p-3">
      <div className="text-xs text-muted-foreground">{title}</div>
      <div className="mt-2 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series}>
            <XAxis dataKey="t" tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}s`} />
            <YAxis domain={domain} tick={{ fontSize: 10 }} width={28} />
            <Tooltip />
            <Line type="monotone" dataKey="v" stroke="currentColor" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

