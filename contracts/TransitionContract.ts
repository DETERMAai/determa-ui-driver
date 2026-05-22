export type TransitionContract = {
  transition_id: string;
  from_state: string;
  to_state: string;
  allowed: boolean;
  reason?: string;
};