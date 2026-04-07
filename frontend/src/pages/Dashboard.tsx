import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, Mic, MicOff, Video, VideoOff } from "lucide-react";
import { startAudioCapture, type AudioCaptureController } from "@/lib/audioCapture";
import { isSpeechRecognitionSupported, startSpeechRecognition, type SpeechRecognitionController } from "@/lib/speechRecognition";
import { startVision, type VisionMetrics } from "@/lib/vision";
import { TranscriptHighlighter } from "@/components/TranscriptHighlighter";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type WsState = "disconnected" | "connecting" | "connected";

export function Dashboard() {
  const [wsState, setWsState] = useState<WsState>("disconnected");
  const [lastAck, setLastAck] = useState<string>("");
  const [transcript, setTranscript] = useState<string>("");
  const [metrics, setMetrics] = useState<any>(null);
  const [series, setSeries] = useState<Array<any>>([]);
  const [micOn, setMicOn] = useState(false);
  const [level, setLevel] = useState(0);
  const [camOn, setCamOn] = useState(false);
  const [vision, setVision] = useState<VisionMetrics | null>(null);
  const [errorText, setErrorText] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);
  const sessionActiveRef = useRef(false);
  const audioRef = useRef<AudioCaptureController | null>(null);
  const speechRef = useRef<SpeechRecognitionController | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const visionRef = useRef<{ stop: () => void } | null>(null);

  const wsUrl = useMemo(() => {
    const api = "ws://localhost:8000/ws/session";
    return api;
  }, []);

  useEffect(() => {
    return () => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN && sessionActiveRef.current) {
        ws.send(JSON.stringify({ type: "session_stop", payload: {} }));
      }
      audioRef.current?.stop();
      audioRef.current = null;
      speechRef.current?.stop();
      speechRef.current = null;
      visionRef.current?.stop();
      visionRef.current = null;
      wsRef.current?.close();
      wsRef.current = null;
      sessionActiveRef.current = false;
    };
  }, []);

  async function ensureConnected(): Promise<WebSocket> {
    const existing = wsRef.current;
    if (existing && existing.readyState === WebSocket.OPEN) {
      return existing;
    }

    if (existing && existing.readyState === WebSocket.CONNECTING) {
      return await new Promise<WebSocket>((resolve, reject) => {
        const onOpen = () => {
          existing.removeEventListener("open", onOpen);
          existing.removeEventListener("error", onErr);
          resolve(existing);
        };
        const onErr = () => {
          existing.removeEventListener("open", onOpen);
          existing.removeEventListener("error", onErr);
          reject(new Error("websocket_connect_failed"));
        };
        existing.addEventListener("open", onOpen, { once: true });
        existing.addEventListener("error", onErr, { once: true });
      });
    }

    if (wsRef.current) wsRef.current.close();
    setWsState("connecting");
    return await new Promise<WebSocket>((resolve, reject) => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => {
        setWsState("connected");
        setErrorText("");
        resolve(ws);
      };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as { type: string; payload: any };
        if (msg.type === "ack") setLastAck(msg.payload?.received_type ?? "");
        if (msg.type === "transcript_partial") setTranscript(msg.payload?.text ?? "");
        if (msg.type === "transcript_final") setTranscript(msg.payload?.text ?? "");
        if (msg.type === "error") setErrorText(msg.payload?.message ?? "Unknown websocket error");
        if (msg.type === "session_saved") {
          if (msg.payload?.transcript) setTranscript(msg.payload.transcript);
          sessionActiveRef.current = false;
          ws.close();
          setWsState("disconnected");
        }
        if (msg.type === "realtime_metrics") {
          setMetrics(msg.payload ?? null);
          const p = msg.payload ?? {};
          setSeries((s) => {
            const next = [...s, { t: (p.t_ms ?? 0) / 1000, wpm: p.wpm ?? 0, conf: p.confidence ?? 0 }];
            return next.length > 240 ? next.slice(-240) : next;
          });
        }
      } catch {
        // ignore
      }
    };
    ws.onclose = () => setWsState("disconnected");
      ws.onerror = () => {
        setWsState("disconnected");
        reject(new Error("websocket_connect_failed"));
      };
    });
  }

  function connect() {
    void ensureConnected();
  }

  async function startMic() {
    const ws = await ensureConnected();
    if (!sessionActiveRef.current && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "session_start", payload: { mode: "practice", startedAt: Date.now() } }));
      sessionActiveRef.current = true;
    }
    setMicOn(true);
    audioRef.current?.stop();
    audioRef.current = await startAudioCapture({
      targetSampleRateHz: 16000,
      chunkMs: 250,
      onLevel: setLevel,
      onChunk: (chunk) => {
        const ws = wsRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        ws.send(JSON.stringify({ type: "audio_chunk", payload: chunk }));
      }
    });

    speechRef.current?.stop();
    speechRef.current = await startSpeechRecognition({
      language: "en-US",
      onTranscript: (text) => {
        setTranscript(text);
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "transcript_update", payload: { text } }));
        }
      },
      onError: (message) => setErrorText(`speech_recognition: ${message}`)
    });
    if (!speechRef.current && !isSpeechRecognitionSupported()) {
      setErrorText("speech_recognition: not supported in this browser/profile")
    }
  }

  function stopMic() {
    setMicOn(false);
    audioRef.current?.stop();
    audioRef.current = null;
    speechRef.current?.stop();
    speechRef.current = null;

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && sessionActiveRef.current) {
      ws.send(JSON.stringify({ type: "session_stop", payload: {} }));
    }
  }

  async function startCam() {
    if (!videoRef.current) return;
    await ensureConnected();
    setCamOn(true);
    visionRef.current?.stop();
    visionRef.current = await startVision({
      videoEl: videoRef.current,
      onMetrics: (m) => {
        setVision(m);
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "video_landmarks", payload: m }));
        }
      }
    });
  }

  function stopCam() {
    setCamOn(false);
    visionRef.current?.stop();
    visionRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Live Coaching Session</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Talk naturally. You’ll see live transcript and coaching metrics update in real time.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={connect}
            className="rounded-xl bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
          >
            {wsState === "connected" ? "Reconnect" : "Connect"}
          </button>
          {micOn ? (
            <button
              type="button"
              onClick={stopMic}
              className="inline-flex items-center gap-2 rounded-xl border border-border/60 px-4 py-2 text-sm font-medium hover:bg-muted/60"
            >
              <MicOff className="h-4 w-4" />
              Stop
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void startMic()}
              className="inline-flex items-center gap-2 rounded-xl border border-border/60 px-4 py-2 text-sm font-medium hover:bg-muted/60"
            >
              <Mic className="h-4 w-4" />
              Start
            </button>
          )}
          {camOn ? (
            <button
              type="button"
              onClick={stopCam}
              className="inline-flex items-center gap-2 rounded-xl border border-border/60 px-4 py-2 text-sm font-medium hover:bg-muted/60"
            >
              <VideoOff className="h-4 w-4" />
              Camera off
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void startCam()}
              className="inline-flex items-center gap-2 rounded-xl border border-border/60 px-4 py-2 text-sm font-medium hover:bg-muted/60"
            >
              <Video className="h-4 w-4" />
              Camera on
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Metric title="WebSocket" value={wsState} detail={lastAck ? `Last ack: ${lastAck}` : "No messages yet"} />
        <Metric
          title="Microphone"
          value={micOn ? "Live" : "Off"}
          detail={`Input level: ${(level * 100).toFixed(0)}%`}
          icon={<Mic className="h-4 w-4" />}
        />
        <Metric title="WPM" value={metrics?.wpm?.toString?.() ?? "—"} detail={metrics?.wpm_label ?? "—"} />
        <Metric title="Confidence" value={metrics?.confidence?.toString?.() ?? "—"} detail={metrics?.confidence_label ?? "—"} />
      </div>

      {errorText ? (
        <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
          Backend error: {errorText}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-border/60 bg-card p-6">
          <div className="text-sm font-medium">Live transcript</div>
          <div className="mt-3 min-h-24 text-sm text-muted-foreground">
            <TranscriptHighlighter text={transcript} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-muted-foreground">
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <div>Fillers</div>
              <div className="mt-1 text-base font-semibold text-foreground">{metrics?.fillers_total ?? "—"}</div>
              <div className="mt-1">Density: {metrics?.fillers_density ?? "—"}</div>
            </div>
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
              <div>Continuity</div>
              <div className="mt-1 text-base font-semibold text-foreground">
                {metrics?.continuity != null ? `${Math.round(metrics.continuity * 100)}%` : "—"}
              </div>
              <div className="mt-1">Keep sentences flowing.</div>
            </div>
          </div>
        </div>
        <div className="rounded-2xl border border-border/60 bg-card p-6">
          <div className="text-sm font-medium">Smart suggestions</div>
          <div className="mt-3 space-y-2 text-sm text-muted-foreground">
            {(metrics?.suggestions ?? ["Suggestions will appear during your session."]).map((s: string, i: number) => (
              <div key={i} className="rounded-xl border border-border/60 bg-muted/40 p-3">
                {s}
              </div>
            ))}
          </div>
          <div className="mt-4">
            <div className="text-sm font-medium">Personalized insights</div>
            <div className="mt-2 space-y-2 text-sm text-muted-foreground">
              {(metrics?.insights ?? []).length ? (
                (metrics.insights as string[]).map((s: string, i: number) => (
                  <div key={i} className="rounded-xl border border-border/60 bg-muted/40 p-3">
                    {s}
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-border/60 bg-muted/20 p-3">
                  Insights appear once we detect stable patterns.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-border/60 bg-card p-6">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">Realtime trends</div>
          <div className="text-xs text-muted-foreground">Last ~4 minutes</div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="h-44 rounded-xl border border-border/60 bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">Words per minute</div>
            <div className="mt-2 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series}>
                  <XAxis dataKey="t" tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}s`} />
                  <YAxis tick={{ fontSize: 10 }} width={28} />
                  <Tooltip />
                  <Line type="monotone" dataKey="wpm" stroke="currentColor" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="h-44 rounded-xl border border-border/60 bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">Confidence</div>
            <div className="mt-2 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series}>
                  <XAxis dataKey="t" tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}s`} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} width={28} />
                  <Tooltip />
                  <Line type="monotone" dataKey="conf" stroke="currentColor" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-border/60 bg-card p-6 md:col-span-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">Camera</div>
            <div className="text-xs text-muted-foreground">
              {vision ? `Emotion: ${vision.emotion}` : "Enable camera to compute landmarks"}
            </div>
          </div>
          <div className="mt-3 overflow-hidden rounded-xl border border-border/60 bg-muted">
            <video ref={videoRef} className="aspect-video w-full object-cover" muted playsInline />
          </div>
        </div>
        <div className="rounded-2xl border border-border/60 bg-card p-6">
          <div className="text-sm font-medium">Visual metrics</div>
          <div className="mt-3 space-y-3 text-sm text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Eye contact</span>
              <span className="font-medium text-foreground">{((vision?.eye_contact ?? metrics?.eye_contact ?? 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Posture</span>
              <span className="font-medium text-foreground">{((vision?.posture ?? metrics?.posture ?? 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Emotion</span>
              <span className="font-medium text-foreground">{vision?.emotion ?? metrics?.emotion ?? "—"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Voice variation</span>
              <span className="font-medium text-foreground">
                {metrics?.voice_variation != null ? `${Math.round(metrics.voice_variation * 100)}%` : "—"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="rounded-2xl border border-border/60 bg-card p-6"
      >
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg border border-border/60 p-2 text-muted-foreground">
            <AlertCircle className="h-4 w-4" />
          </div>
          <div className="space-y-1">
            <div className="text-sm font-medium">Next up</div>
            <div className="text-sm text-muted-foreground">
              Voice modulation (pitch variation) is next, then session persistence + reports + progress analytics.
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function Metric({
  title,
  value,
  detail,
  icon
}: {
  title: string;
  value: string;
  detail: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-border/60 bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-muted-foreground">{title}</div>
        {icon ? <div className="text-muted-foreground">{icon}</div> : null}
      </div>
      <div className="mt-2 text-2xl font-semibold capitalize">{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{detail}</div>
    </div>
  );
}

