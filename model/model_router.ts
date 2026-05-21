import { FreeLLMAPIModel } from './freellmapi_model.js';
import type { ModelProvider, ModelProviderName } from './provider.js';

const DEFAULT_FREELLMAPI_URL = 'http://localhost:3001/v1/chat/completions';
const DEFAULT_LOCAL_MODEL_URL = process.env.LOCAL_MODEL_URL ?? DEFAULT_FREELLMAPI_URL;

function readProviderName(): ModelProviderName {
  const raw = String(process.env.DETERMA_MODEL_PROVIDER ?? 'local').trim().toLowerCase();
  if (raw === 'freellmapi') return 'freellmapi';
  return 'local';
}

function createProviderByName(name: ModelProviderName): ModelProvider {
  if (name === 'freellmapi') {
    const url = process.env.FREELLMAPI_URL ?? DEFAULT_FREELLMAPI_URL;
    return new FreeLLMAPIModel(url, { model: process.env.FREELLMAPI_MODEL ?? 'gpt-3.5-turbo' });
  }

  return new FreeLLMAPIModel(DEFAULT_LOCAL_MODEL_URL, {
    model: process.env.LOCAL_MODEL_NAME ?? process.env.FREELLMAPI_MODEL ?? 'gpt-3.5-turbo',
  });
}

let activeProviderName: ModelProviderName = readProviderName();
let activeProvider: ModelProvider = createProviderByName(activeProviderName);

export function refreshModelProvider(): void {
  activeProviderName = readProviderName();
  activeProvider = createProviderByName(activeProviderName);
}

export function getActiveModelProviderName(): ModelProviderName {
  return activeProviderName;
}

export async function generateModel(prompt: string): Promise<string> {
  return activeProvider.generate(prompt);
}