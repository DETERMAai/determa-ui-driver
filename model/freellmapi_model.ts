import type { ModelProvider, ModelProviderConfig } from './provider.js';

export class FreeLLMAPIModel implements ModelProvider {
  readonly providerName = 'freellmapi';
  private readonly url: string;
  private readonly model: string;
  private readonly timeoutMs: number;

  constructor(url: string, config: ModelProviderConfig = {}) {
    this.url = url;
    this.model = config.model ?? process.env.FREELLMAPI_MODEL ?? 'gpt-3.5-turbo';
    this.timeoutMs = config.timeoutMs ?? 45000;
  }

  async generate(prompt: string): Promise<string> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(this.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: this.model,
          messages: [
            {
              role: 'user',
              content: prompt,
            },
          ],
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorBody = await response.text().catch(() => '');
        throw new Error(`freellmapi request failed (${response.status}): ${errorBody || response.statusText}`);
      }

      const data: any = await response.json();
      const content = data?.choices?.[0]?.message?.content;
      if (typeof content !== 'string' || content.trim().length === 0) {
        throw new Error('freellmapi response missing choices[0].message.content');
      }

      return content;
    } finally {
      clearTimeout(timeout);
    }
  }
}