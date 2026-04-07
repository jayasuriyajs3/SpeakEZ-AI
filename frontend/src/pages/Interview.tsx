import { useEffect, useMemo, useRef, useState } from "react";
import { Mic, MicOff, Timer } from "lucide-react";
import { startAudioCapture, type AudioCaptureController } from "@/lib/audioCapture";
import { TranscriptHighlighter } from "@/components/TranscriptHighlighter";

type Question = { id: string; category: string; difficulty: string; text: string };

export function Interview() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [idx, setIdx] = useState(0);
  const [micOn, setMicOn] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [metrics, setMetrics] = useState<any>(null);
  const [timerSec, setTimerSec] = useState(180);
  const [running, setRunning] = useState(false);
  const [score, setScore] = useState<any>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<AudioCaptureController | null>(null);

  const wsUrl = useMemo(() => "ws://localhost:8000/ws/session", []);

  useEffect(() => {
    fetch("http://localhost:8000/api/interview/questions")
      .then((r) => r.json())
      .then(setQuestions)
      .catch(() => setQuestions([]));
  }, []);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setTimerSec((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [running]);

  useEffect(() => {
    if (timerSec === 0 && running) {
      stop();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timerSec]);

  function connect() {
    if (wsRef.current) wsRef.current.close();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify({ type: "session_start", payload: { mode: "interview" } }));
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as { type: string; payload: any };
        if (msg.type === "transcript_partial") setTranscript(msg.payload?.text ?? "");
        if (msg.type === "realtime_metrics") setMetrics(msg.payload ?? null);
        if (msg.type === "session_saved") {
          // session id can be used to generate a report later
        }
      } catch {
        // ignore
      }
    };
  }

  async function start() {
    setScore(null);
    setTranscript("");
    setTimerSec(180);
    setRunning(true);
    connect();
    setMicOn(true);
    audioRef.current?.stop();
    audioRef.current = await startAudioCapture({
      targetSampleRateHz: 16000,
      chunkMs: 250,
      onChunk: (chunk) => {
        const ws = wsRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        ws.send(JSON.stringify({ type: "audio_chunk", payload: chunk }));
      }
    });
  }

  async function stop() {
    setRunning(false);
    setMicOn(false);
    audioRef.current?.stop();
    audioRef.current = null;
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "session_stop", payload: {} }));
    }
    // Score the interview answer
    try {
      const res = await fetch("http://localhost:8000/api/interview/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: transcript, confidence: metrics?.confidence ?? 0 })
      });
      setScore(await res.json());
    } catch {
      setScore(null);
    }
  }

  const q = questions[idx];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">AI Interview Simulator</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Placement Mode: answer within the timer, then get a rubric score plus your communication metrics.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {micOn ? (
            <button
              type="button"
              onClick={() => void stop()}
              className="inline-flex items-center gap-2 rounded-xl border border-border/60 px-4 py-2 text-sm font-medium hover:bg-muted/60"
            >
              <MicOff className="h-4 w-4" />
              Stop
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void start()}
              className="inline-flex items-center gap-2 rounded-xl bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
            >
              <Mic className="h-4 w-4" />
              Start
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-border/60 bg-card p-6 md:col-span-2">
          <div className="text-sm font-medium">Question</div>
          <div className="mt-3 text-lg font-semibold">{q?.text ?? "Loading questions..."}</div>
          <div className="mt-2 text-xs text-muted-foreground">
            {q ? `${q.category} • ${q.difficulty}` : ""}
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={() => setIdx((i) => Math.max(0, i - 1))}
              className="rounded-xl border border-border/60 px-4 py-2 text-sm font-medium hover:bg-muted/60"
              disabled={idx === 0}
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => setIdx((i) => Math.min(questions.length - 1, i + 1))}
              className="rounded-xl border border-border/60 px-4 py-2 text-sm font-medium hover:bg-muted/60"
              disabled={idx >= questions.length - 1}
            >
              Next
            </button>
          </div>
        </div>
        <div className="rounded-2xl border border-border/60 bg-card p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">Timer</div>
            <Timer className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="mt-3 text-3xl font-semibold tabular-nums">
            {Math.floor(timerSec / 60)}:{String(timerSec % 60).padStart(2, "0")}
          </div>
          <div className="mt-3 text-xs text-muted-foreground">Default: 3 minutes. Stops automatically at 0.</div>
          <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-muted-foreground">
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <div>Confidence</div>
              <div className="mt-1 text-base font-semibold text-foreground">{metrics?.confidence ?? "—"}</div>
            </div>
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <div>WPM</div>
              <div className="mt-1 text-base font-semibold text-foreground">{metrics?.wpm ?? "—"}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-border/60 bg-card p-6">
          <div className="text-sm font-medium">Your answer (live)</div>
          <div className="mt-3 text-sm text-muted-foreground">
            <TranscriptHighlighter text={transcript} />
          </div>
        </div>
        <div className="rounded-2xl border border-border/60 bg-card p-6">
          <div className="text-sm font-medium">Evaluation</div>
          {score ? (
            <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-muted-foreground">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <div>Content score</div>
                <div className="mt-1 text-2xl font-semibold text-foreground">{score.content}</div>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
                <div>Overall</div>
                <div className="mt-1 text-2xl font-semibold text-foreground">{score.overall}</div>
              </div>
              <div className="col-span-2 rounded-xl border border-border/60 bg-muted/20 p-3 text-sm">
                Tip: add a quick structure (Situation → Action → Result) and include a measurable impact.
              </div>
            </div>
          ) : (
            <div className="mt-3 text-sm text-muted-foreground">Stop the timer to generate a score.</div>
          )}
        </div>
      </div>
    </div>
  );
}

