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

import { cn } from '@/lib/utils';
import { Gavel, LineChart, Settings } from 'lucide-react';
import { Suspense } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

/**
 * Minimal application shell for the VC startup-evaluation app.
 *
 * This is a deliberately lightweight replacement for eigent's full Layout: it
 * skips the install/onboarding/backend-health gating and exposes only the two
 * surfaces this product needs — Analyze and Settings. All of eigent's original
 * navigation (Channels, Connectors, Browser, Remote Control, History,
 * Workspace) is simply not rendered here (the code is retained elsewhere).
 */

type NavItem = {
  to: string;
  label: string;
  icon: React.ReactNode;
};

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Analyze', icon: <LineChart className="h-4 w-4" /> },
  { to: '/settings', label: 'Settings', icon: <Settings className="h-4 w-4" /> },
];

const VCLayout = () => {
  return (
    <div className="bg-ds-bg-neutral-muted-default flex h-full flex-col overflow-hidden">
      <header className="border-ds-border-neutral-subtle-default flex h-14 shrink-0 items-center gap-6 border-b px-6">
        <div className="flex items-center gap-2">
          <span className="bg-ds-bg-neutral-default-active flex h-7 w-7 items-center justify-center rounded-md">
            <Gavel className="text-ds-icon-neutral-default-default h-4 w-4" />
          </span>
          <span className="text-ds-text-neutral-default-default text-sm font-semibold">
            Verdict
          </span>
        </div>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-ds-bg-neutral-default-active text-ds-text-neutral-default-default'
                    : 'text-ds-text-neutral-subtle-default hover:bg-ds-bg-neutral-default-hover'
                )
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="min-h-0 flex-1 overflow-y-auto">
        <Suspense
          fallback={
            <div className="flex h-full items-center justify-center">
              <div className="border-ds-border-neutral-subtle-default h-8 w-8 animate-spin rounded-full border-b-2" />
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
};

export default VCLayout;
