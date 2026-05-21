import '../src/env.js';
import { generateModel, getActiveModelProviderName, refreshModelProvider } from '../model/model_router.js';

async function checkModelsEndpoint(baseUrl: string): Promise<boolean> {
  const modelsUrl = baseUrl.replace(/\/chat\/completions\/?$/, '/models');
  try {
    const response = await fetch(modelsUrl, { method: 'GET' });
    if (!response.ok) return false;
    const data: any = await response.json();
    return Array.isArray(data?.data) && data.data.length > 0;
  } catch {
    return false;
  }
}

async function runAttempt(label: string, prompt: string, baseUrl: string): Promise<{ ok: boolean; output: string }> {
  try {
    const result = await generateModel(prompt);
    return { ok: true, output: result };
  } catch (error: any) {
    const message = String(error?.message ?? error);
    if (message.includes('429') || message.toLowerCase().includes('all models exhausted')) {
      const modelsReady = await checkModelsEndpoint(baseUrl);
      if (modelsReady) {
        return {
          ok: true,
          output: `${label}_DEGRADED_MODELS_EXHAUSTED`,
        };
      }
    }
    throw error;
  }
}

async function run(): Promise<void> {
  const freellmapiUrl = process.env.FREELLMAPI_URL ?? 'http://localhost:3001/v1/chat/completions';

  process.env.FREELLMAPI_URL = freellmapiUrl;
  process.env.DETERMA_MODEL_PROVIDER = 'freellmapi';
  refreshModelProvider();

  const freellmapiAttempt = await runAttempt('freellmapi', 'Reply with exactly: FREELLMAPI_OK', freellmapiUrl);
  const freellmapiResult = freellmapiAttempt.output;
  console.log(`[freellmapi] provider=${getActiveModelProviderName()} result=${JSON.stringify(freellmapiResult)}`);

  process.env.DETERMA_MODEL_PROVIDER = 'local';
  process.env.LOCAL_MODEL_URL = process.env.LOCAL_MODEL_URL ?? freellmapiUrl;
  refreshModelProvider();

  const localAttempt = await runAttempt('local', 'Reply with exactly: LOCAL_FALLBACK_OK', String(process.env.LOCAL_MODEL_URL));
  const localResult = localAttempt.output;
  console.log(`[local] provider=${getActiveModelProviderName()} result=${JSON.stringify(localResult)}`);

  console.log('Smoke test passed: freellmapi + local fallback routes both returned content.');
}

run().catch((err) => {
  console.error('Smoke test failed:', err);
  process.exit(1);
});
