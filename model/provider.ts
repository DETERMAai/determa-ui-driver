export interface ModelProvider {
  readonly providerName: string;
  generate(prompt: string): Promise<string>;
}

export type ModelProviderName = 'freellmapi' | 'local';

export interface ModelProviderConfig {
  model?: string;
  timeoutMs?: number;
}