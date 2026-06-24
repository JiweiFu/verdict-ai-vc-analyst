// ========= Copyright 2025-2026 @ Eigent.ai All Rights Reserved. =========
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// ========= Copyright 2025-2026 @ Eigent.ai All Rights Reserved. =========

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/** Supported LLM providers for the VC analysis backend. */
export type VCProvider = 'anthropic' | 'openai' | 'deepseek';

/** Display + default-model metadata for a provider. */
export interface VCProviderMeta {
  id: VCProvider;
  label: string;
  defaultModel: string;
}

/** Source of truth for the provider list rendered in Settings. */
export const VC_PROVIDERS: VCProviderMeta[] = [
  { id: 'anthropic', label: 'Anthropic (Claude)', defaultModel: 'claude-opus-4-8' },
  { id: 'openai', label: 'OpenAI (GPT)', defaultModel: 'gpt-4o' },
  { id: 'deepseek', label: 'DeepSeek', defaultModel: 'deepseek-chat' },
];

/** Returns the default model id for a provider, or '' if unknown. */
export function defaultModelFor(provider: VCProvider): string {
  return VC_PROVIDERS.find((p) => p.id === provider)?.defaultModel ?? '';
}

interface VCSettingsState {
  provider: VCProvider; // default provider selected in Settings
  apiKeys: Record<VCProvider, string>; // BYO key per provider — localStorage only
  setProvider: (p: VCProvider) => void;
  setApiKey: (p: VCProvider, key: string) => void;
}

/**
 * VC settings store. The API keys live ONLY in localStorage (via the persist
 * middleware below) and are never transmitted from this store — the analysis
 * backend is the sole consumer and reads them at request time elsewhere.
 */
export const useVCSettingsStore = create<VCSettingsState>()(
  persist(
    (set) => ({
      provider: 'anthropic',
      apiKeys: { anthropic: '', openai: '', deepseek: '' },
      setProvider: (p) => set({ provider: p }),
      setApiKey: (p, key) =>
        set((state) => ({ apiKeys: { ...state.apiKeys, [p]: key } })),
    }),
    { name: 'vc-settings' }
  )
);
