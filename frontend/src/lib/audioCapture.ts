import { bytesToBase64 } from "@/lib/base64";

type AudioChunkHandler = (chunk: { pcm16_b64: string; sample_rate_hz: number }) => void;
type LevelHandler = (rms: number) => void;

export type AudioCaptureController = {
  stop: () => void;
};

function floatTo16BitPCM(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function downsampleBuffer(input: Float32Array, inputRate: number, outputRate: number): Float32Array {
  if (outputRate === inputRate) return input;
  const ratio = inputRate / outputRate;
  const newLen = Math.round(input.length / ratio);
  const result = new Float32Array(newLen);
  let offset = 0;
  for (let i = 0; i < newLen; i++) {
    const nextOffset = Math.round((i + 1) * ratio);
    let sum = 0;
    let count = 0;
    for (let j = offset; j < nextOffset && j < input.length; j++) {
      sum += input[j];
      count++;
    }
    result[i] = count ? sum / count : 0;
    offset = nextOffset;
  }
  return result;
}

export async function startAudioCapture(opts: {
  targetSampleRateHz?: number;
  chunkMs?: number;
  onChunk: AudioChunkHandler;
  onLevel?: LevelHandler;
}): Promise<AudioCaptureController> {
  const targetSampleRateHz = opts.targetSampleRateHz ?? 16000;
  const chunkMs = opts.chunkMs ?? 250;

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const source = audioCtx.createMediaStreamSource(stream);

  const processor = audioCtx.createScriptProcessor(4096, 1, 1);
  const buffer: Float32Array[] = [];
  let bufferedSamples = 0;

  const flushTargetSamples = Math.round((targetSampleRateHz * chunkMs) / 1000);

  processor.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0);
    const rms = Math.sqrt(input.reduce((acc, v) => acc + v * v, 0) / input.length);
    opts.onLevel?.(rms);

    const down = downsampleBuffer(input, audioCtx.sampleRate, targetSampleRateHz);
    buffer.push(down);
    bufferedSamples += down.length;

    if (bufferedSamples >= flushTargetSamples) {
      const merged = new Float32Array(bufferedSamples);
      let o = 0;
      for (const b of buffer) {
        merged.set(b, o);
        o += b.length;
      }
      buffer.length = 0;
      bufferedSamples = 0;

      const pcm16 = floatTo16BitPCM(merged);
      const bytes = new Uint8Array(pcm16.buffer);
      opts.onChunk({ pcm16_b64: bytesToBase64(bytes), sample_rate_hz: targetSampleRateHz });
    }
  };

  source.connect(processor);
  processor.connect(audioCtx.destination);

  return {
    stop: () => {
      processor.disconnect();
      source.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      audioCtx.close().catch(() => undefined);
    }
  };
}

