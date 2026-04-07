import React from "react";

const FILLERS = ["um", "uh", "like", "you know", "actually", "basically", "so"];

function escapeRegExp(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function TranscriptHighlighter({ text }: { text: string }) {
  if (!text) return <span className="text-muted-foreground">Start speaking to generate a transcript...</span>;

  const pattern = new RegExp(`\\b(${FILLERS.map(escapeRegExp).join("|")})\\b`, "gi");
  const parts = text.split(pattern);

  return (
    <span className="whitespace-pre-wrap">
      {parts.map((p, i) => {
        const isFiller = FILLERS.includes(p.toLowerCase());
        if (!isFiller) return <React.Fragment key={i}>{p}</React.Fragment>;
        return (
          <mark
            key={i}
            className="rounded-md bg-amber-500/20 px-1 py-0.5 font-medium text-amber-200 dark:text-amber-200"
          >
            {p}
          </mark>
        );
      })}
    </span>
  );
}

