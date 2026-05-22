export type MutationContract = {
  mutation_id: string;
  actor: string;
  scope: string;
  requested_at_iso: string;
  expires_at_iso?: string;
};