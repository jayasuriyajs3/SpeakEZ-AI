import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export function Landing() {
  return (
    <div className="space-y-16">
      <section className="grid gap-8 rounded-2xl border border-border/60 bg-card p-8 md:grid-cols-2 md:p-12">
        <div className="space-y-5">
          <div className="inline-flex items-center rounded-full border border-border/60 bg-muted px-3 py-1 text-xs text-muted-foreground">
            Real-time coaching for students
          </div>
          <h1 className="text-balance text-4xl font-semibold tracking-tight md:text-5xl">
            SPEAKEZ AI
            <span className="block text-muted-foreground">Real-Time Communication Coach</span>
          </h1>
          <p className="text-pretty text-base text-muted-foreground md:text-lg">
            Practice presentations and interviews with live feedback on fillers, pace, confidence, eye contact, posture,
            and voice variation.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/dashboard"
              className="rounded-xl bg-foreground px-5 py-3 text-sm font-medium text-background hover:opacity-90"
            >
              Start a live session
            </Link>
            <Link
              to="/interview"
              className="rounded-xl border border-border/60 px-5 py-3 text-sm font-medium text-foreground hover:bg-muted/60"
            >
              Interview simulator
            </Link>
            <Link
              to="/analytics"
              className="rounded-xl border border-border/60 px-5 py-3 text-sm font-medium text-foreground hover:bg-muted/60"
            >
              View progress
            </Link>
          </div>
        </div>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative overflow-hidden rounded-2xl border border-border/60 bg-muted p-6"
        >
          <div className="space-y-3">
            <div className="text-sm font-medium">Live Dashboard Preview</div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { k: "WPM", v: "146", s: "Optimal" },
                { k: "Fillers", v: "7", s: "Lower is better" },
                { k: "Confidence", v: "78", s: "Good" },
                { k: "Eye contact", v: "82%", s: "Keep it up" }
              ].map((m) => (
                <div key={m.k} className="rounded-xl border border-border/60 bg-card p-4">
                  <div className="text-xs text-muted-foreground">{m.k}</div>
                  <div className="mt-1 text-2xl font-semibold">{m.v}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{m.s}</div>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-border/60 bg-card p-4 text-sm text-muted-foreground">
              “Try to reduce ‘like’ and keep a steadier pace after the first minute.”
            </div>
          </div>
        </motion.div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          {
            title: "Accurate speech-to-text",
            body: "Local Whisper by default, with optional cloud STT for maximum accuracy."
          },
          { title: "Realtime multimodal coaching", body: "Fillers, pace, voice variation + webcam-based eye contact and posture." },
          { title: "Progress analytics", body: "Session history, trends, and exportable reports." }
        ].map((f) => (
          <div key={f.title} className="rounded-2xl border border-border/60 bg-card p-6">
            <div className="text-base font-semibold">{f.title}</div>
            <div className="mt-2 text-sm text-muted-foreground">{f.body}</div>
          </div>
        ))}
      </section>
    </div>
  );
}

