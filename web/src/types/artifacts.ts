export type ArtifactManifest = {
  updated_at: string;
  storage: string;
  artifacts: {
    video: { ready: boolean; url?: string };
    cv1_shots: { ready: boolean; count?: number };
    cv2_keyframes: {
      ready: boolean;
      count?: number;
      items?: { path: string; url: string; window_id: string }[];
    };
    transcript?: { ready: boolean; segments?: number };
    plan: { ready: boolean; moments?: number; skill?: string };
    summary: { ready: boolean };
    cv3_dedup: { ready: boolean; note?: string };
  };
};

export type Shot = { id: number; start: number; end: number };

export type ShotPreview = Shot & {
  t?: number;
  path?: string;
  thumb_url: string;
};

export type ShotsArtifact = {
  shots: Shot[];
  previews: ShotPreview[];
  count: number;
};

export type Plan = {
  skill: string;
  target_seconds: number;
  moments: {
    label?: string;
    score?: number;
    reason?: string;
    clip: { start: number; end: number };
    keyframes?: { path: string; sharpness?: number; t?: number }[];
  }[];
};
