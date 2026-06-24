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

import * as React from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  VC_PROVIDERS,
  useVCSettingsStore,
  type VCProvider,
} from '@/store/vcSettingsStore';

/** Per-field show/hide state for the password inputs. */
type RevealState = Record<VCProvider, boolean>;

const INITIAL_REVEAL: RevealState = {
  anthropic: false,
  openai: false,
  deepseek: false,
};

export default function VCSettings(): React.ReactElement {
  const provider = useVCSettingsStore((s) => s.provider);
  const apiKeys = useVCSettingsStore((s) => s.apiKeys);
  const setProvider = useVCSettingsStore((s) => s.setProvider);
  const setApiKey = useVCSettingsStore((s) => s.setApiKey);

  const [revealed, setRevealed] = React.useState<RevealState>(INITIAL_REVEAL);

  const toggleReveal = (id: VCProvider): void =>
    setRevealed((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="mx-auto w-full max-w-2xl px-6 py-10">
      <div className="mb-8 space-y-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-ds-text-neutral-default-default">
          Settings
        </h1>
        <p className="text-sm text-ds-text-neutral-muted-default">
          Your API keys are stored locally in this app and are only ever sent to
          the analysis backend.
        </p>
      </div>

      <div className="space-y-6">
        {/* Default provider */}
        <Card className="border-ds-border-neutral-default-default bg-ds-bg-neutral-default-default">
          <CardHeader>
            <CardTitle className="text-base">Default provider</CardTitle>
            <CardDescription>
              The provider used for new analysis runs.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Label className="mb-1.5 block text-ds-text-neutral-default-default">
              Provider
            </Label>
            <Select
              value={provider}
              onValueChange={(value) => setProvider(value as VCProvider)}
            >
              <SelectTrigger wrapperClassName="w-full">
                <SelectValue placeholder="Select a provider" />
              </SelectTrigger>
              <SelectContent>
                {VC_PROVIDERS.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        {/* API keys per provider */}
        <Card className="border-ds-border-neutral-default-default bg-ds-bg-neutral-default-default">
          <CardHeader>
            <CardTitle className="text-base">API keys</CardTitle>
            <CardDescription>
              Bring your own key for each provider. Keys are saved as you type.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {VC_PROVIDERS.map((p) => {
              const isRevealed = revealed[p.id];
              return (
                <div key={p.id} className="space-y-1.5">
                  <Label
                    htmlFor={`vc-api-key-${p.id}`}
                    className="block text-ds-text-neutral-default-default"
                  >
                    {p.label}
                  </Label>
                  <Input
                    id={`vc-api-key-${p.id}`}
                    type={isRevealed ? 'text' : 'password'}
                    autoComplete="off"
                    spellCheck={false}
                    placeholder="sk-..."
                    value={apiKeys[p.id]}
                    onChange={(e) => setApiKey(p.id, e.target.value)}
                    backIcon={isRevealed ? <EyeOff /> : <Eye />}
                    onBackIconClick={() => toggleReveal(p.id)}
                  />
                  <p className="text-xs text-ds-text-neutral-muted-default">
                    Used for {p.label} requests only
                  </p>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Reassurance note */}
        <div className="flex items-start gap-2 px-1 text-xs text-ds-text-neutral-muted-default">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ds-icon-neutral-default-default" />
          <span>
            Keys never leave this device, except in the analyze request to the
            local backend.
          </span>
        </div>
      </div>
    </div>
  );
}
