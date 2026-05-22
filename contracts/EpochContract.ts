export type EpochContract = {
  epoch_id: string;
  started_at_iso: string;
  closed_at_iso?: string;
  rollback_window_seconds: number;
};