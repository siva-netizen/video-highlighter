export type JobEvent = {
  ts: string;
  kind: string;
  title: string;
  detail: string;
  data?: Record<string, unknown>;
};
