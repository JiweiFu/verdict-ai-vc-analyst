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

import VCLayout from '@/components/VCLayout';
import { lazy } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

// Lazy load page components
const VCAnalysis = lazy(() => import('@/pages/VCAnalysis'));
const VCSettings = lazy(() => import('@/pages/VCSettings'));

// Dev route guard: authentication is intentionally bypassed for the VC app.
// The product is bring-your-own-key (the key is supplied per request from
// Settings), so there is no login. This pass-through keeps the route structure
// intact while removing the auth gate.
const ProtectedRoute = () => <Outlet />;

// Main route configuration: VC Analysis is the home page.
const AppRoutes = () => (
  <Routes>
    <Route element={<ProtectedRoute />}>
      <Route element={<VCLayout />}>
        <Route path="/" element={<VCAnalysis />} />
        <Route path="/settings" element={<VCSettings />} />
      </Route>
    </Route>
    {/* Unknown paths fall back to the analysis home. */}
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default AppRoutes;
