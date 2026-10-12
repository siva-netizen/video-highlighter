export type JobMeta = {
  id: string;
  status: string;
  stage?: string;
  error?: string;
  video_url?: string;
  target_seconds?: number;
  skill?: string;
  progress_pct?: number;
  progress_stage?: string;
  progress_message?: string;
  estimated_completion_at?: string;
  filename?: string;
  can_resume?: boolean;
  looks_stale?: boolean;
  resume_hint?: string;
  resumed_at?: string;
};
