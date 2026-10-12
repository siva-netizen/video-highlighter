export type JobHistoryItem = {
  id: string;
  status: string;
  filename?: string;
  target_seconds?: number;
  skill?: string;
  progress_pct?: number;
  created_at?: string;
  started_at?: string;
  has_video?: boolean;
  can_resume?: boolean;
};
