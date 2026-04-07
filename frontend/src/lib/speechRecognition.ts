export type SpeechRecognitionController = {
  stop: () => void;
};

type SpeechRecognitionCtor = {
  new (): {
    lang: string;
    continuous: boolean;
    interimResults: boolean;
    maxAlternatives: number;
    onresult: ((event: any) => void) | null;
    onerror: ((event: any) => void) | null;
    onend: (() => void) | null;
    start: () => void;
    stop: () => void;
  };
};

type SpeechWindow = Window & {
  webkitSpeechRecognition?: SpeechRecognitionCtor;
  SpeechRecognition?: SpeechRecognitionCtor;
};

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as SpeechWindow;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function isSpeechRecognitionSupported(): boolean {
  return getSpeechRecognitionCtor() != null;
}

export async function startSpeechRecognition(opts: {
  language?: string;
  onTranscript: (text: string) => void;
  onError?: (message: string) => void;
}): Promise<SpeechRecognitionController | null> {
  const Ctor = getSpeechRecognitionCtor();
  if (!Ctor) return null;

  const recognition = new Ctor();
  recognition.lang = opts.language ?? "en-US";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  let committed = "";
  let stopped = false;

  const joinText = (base: string, next: string) => {
    const cleanBase = base.trim();
    const cleanNext = next.trim();
    if (!cleanBase) return cleanNext;
    if (!cleanNext) return cleanBase;
    return `${cleanBase} ${cleanNext}`.trim();
  };

  recognition.onresult = (event: any) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const text = result[0]?.transcript?.trim() ?? "";
      if (!text) continue;
      if (result.isFinal) {
        committed = joinText(committed, text);
      } else {
        interim = joinText(interim, text);
      }
    }
    opts.onTranscript(joinText(committed, interim));
  };

  recognition.onerror = (event: any) => {
    opts.onError?.(event.error || "speech_recognition_error");
  };

  recognition.onend = () => {
    if (stopped) return;
    try {
      recognition.start();
    } catch {
      // ignore auto-restart errors
    }
  };

  recognition.start();

  return {
    stop: () => {
      try {
        stopped = true;
        recognition.onresult = null;
        recognition.onerror = null;
        recognition.onend = null;
        recognition.stop();
      } catch {
        // ignore
      }
    }
  };
}
