import { FaceLandmarker, PoseLandmarker, FilesetResolver, type NormalizedLandmark } from "@mediapipe/tasks-vision";

export type VisionMetrics = {
  eye_contact: number; // 0..1
  posture: number; // 0..1
  emotion: "happy" | "neutral" | "nervous" | "stressed";
};

type VisionHandle = {
  stop: () => void;
};

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

function dist(a: NormalizedLandmark, b: NormalizedLandmark) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

function midpoint(a: NormalizedLandmark, b: NormalizedLandmark): NormalizedLandmark {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, z: 0, visibility: 1 };
}

function computeEyeContact(face: NormalizedLandmark[]) {
  // Very lightweight proxy: if nose tip is centered between eyes, assume looking roughly at camera.
  // Face landmark indices in MediaPipe face mesh:
  // - left eye outer corner ~ 33, right eye outer corner ~ 263, nose tip ~ 1 (approx)
  const leftEye = face[33];
  const rightEye = face[263];
  const nose = face[1];
  if (!leftEye || !rightEye || !nose) return 0;
  const eyeMid = midpoint(leftEye, rightEye);
  const eyeDist = Math.max(1e-6, dist(leftEye, rightEye));
  const noseOffset = Math.abs(nose.x - eyeMid.x) / eyeDist; // normalized
  return clamp01(1 - noseOffset * 2.2);
}

function computePosture(pose: NormalizedLandmark[]) {
  // Proxy: shoulders level + head roughly centered over shoulders.
  // Pose indices: left shoulder 11, right shoulder 12, nose 0
  const ls = pose[11];
  const rs = pose[12];
  const nose = pose[0];
  if (!ls || !rs || !nose) return 0;
  const shMid = midpoint(ls, rs);
  const shoulderDist = Math.max(1e-6, dist(ls, rs));
  const level = 1 - clamp01(Math.abs(ls.y - rs.y) / 0.08);
  const headCentered = 1 - clamp01(Math.abs(nose.x - shMid.x) / (shoulderDist * 1.2));
  return clamp01(0.55 * level + 0.45 * headCentered);
}

function computeEmotion(faceBlendshapes?: Array<{ categories: Array<{ categoryName: string; score: number }> }>) {
  // Baseline: use smile + brow tension proxies.
  // If blendshapes not available, return neutral.
  const cats = faceBlendshapes?.[0]?.categories ?? [];
  const get = (name: string) => cats.find((c) => c.categoryName === name)?.score ?? 0;
  const smile = Math.max(get("mouthSmileLeft"), get("mouthSmileRight"));
  const browDown = Math.max(get("browDownLeft"), get("browDownRight"));
  const jawOpen = get("jawOpen");
  if (smile > 0.35) return "happy" as const;
  if (browDown > 0.35 && jawOpen > 0.25) return "stressed" as const;
  if (jawOpen > 0.35 && smile < 0.2) return "nervous" as const;
  return "neutral" as const;
}

export async function startVision(opts: {
  videoEl: HTMLVideoElement;
  onMetrics: (m: VisionMetrics) => void;
  fps?: number;
}): Promise<VisionHandle> {
  const fps = opts.fps ?? 6;
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  opts.videoEl.srcObject = stream;
  await opts.videoEl.play();

  const resolver = await FilesetResolver.forVisionTasks(
    // CDN-hosted WASM assets (works without extra files in repo)
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm"
  );

  const face = await FaceLandmarker.createFromOptions(resolver, {
    baseOptions: {
      modelAssetPath:
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    },
    runningMode: "VIDEO",
    outputFaceBlendshapes: true,
    numFaces: 1
  });

  const pose = await PoseLandmarker.createFromOptions(resolver, {
    baseOptions: {
      modelAssetPath:
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
    },
    runningMode: "VIDEO",
    numPoses: 1
  });

  let raf = 0;
  let last = 0;
  const step = (ts: number) => {
    raf = requestAnimationFrame(step);
    if (ts - last < 1000 / fps) return;
    last = ts;
    const now = performance.now();
    const faceRes = face.detectForVideo(opts.videoEl, now);
    const poseRes = pose.detectForVideo(opts.videoEl, now);

    const faceLm = faceRes.faceLandmarks?.[0];
    const poseLm = poseRes.landmarks?.[0];
    if (!faceLm || !poseLm) return;
    const eye_contact = computeEyeContact(faceLm);
    const posture = computePosture(poseLm);
    const emotion = computeEmotion(faceRes.faceBlendshapes);
    opts.onMetrics({ eye_contact, posture, emotion });
  };
  raf = requestAnimationFrame(step);

  return {
    stop: () => {
      cancelAnimationFrame(raf);
      face.close();
      pose.close();
      stream.getTracks().forEach((t) => t.stop());
    }
  };
}

