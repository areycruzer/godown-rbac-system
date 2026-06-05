# Next.js Frontend Integration for RBAC and Feature Flags

This directory provides a reference implementation in TypeScript for integrating your Next.js frontend with Godown's dynamic RBAC and Feature Controls.

---

## Structure

- [`lib/api.ts`](file:///Users/cruzer/Documents/projects/intern%20ass/godown/django-saas-kit/examples/frontend/lib/api.ts) — Simple fetch wrapper to get authorization context from `/api/v1/rbac/<tenant_id>/me/`.
- [`contexts/AuthContext.tsx`](file:///Users/cruzer/Documents/projects/intern%20ass/godown/django-saas-kit/examples/frontend/contexts/AuthContext.tsx) — A React context provider to store current role, permissions list, active feature flags, and provide easy checking helpers (`hasPermission`, `isFeatureActive`).
- [`components/Guard.tsx`](file:///Users/cruzer/Documents/projects/intern%20ass/godown/django-saas-kit/examples/frontend/components/Guard.tsx) — A declarative wrapper component to guard UI elements.

---

## Integration Guide

### 1. Set Up Provider

Wrap your application root (e.g. `pages/_app.tsx` or a layout component in App Router) with the `AuthProvider`:

```tsx
import { AuthProvider } from '@/contexts/AuthContext';

export default function App({ Component, pageProps }) {
  // Assuming these are loaded from session / cookie state:
  const apiBaseUrl = "http://localhost:8000";
  const currentTenantId = "a2bd29e8-7efd-4d2a-89a3-5cbe36006767";
  const userToken = "your_jwt_access_token";

  return (
    <AuthProvider apiBaseUrl={apiBaseUrl} tenantId={currentTenantId} token={userToken}>
      <Component {...pageProps} />
    </AuthProvider>
  );
}
```

### 2. Using Hook Helpers

You can check capabilities programmatically in your page or component logic using the `useAuth` hook:

```tsx
import { useAuth } from '@/contexts/AuthContext';

export default function DashboardPage() {
  const { role, hasPermission, isFeatureActive } = useAuth();

  return (
    <div>
      <h1>Workspace Dashboard</h1>
      <p>Current Role: {role?.name}</p>

      {hasPermission('billing:write') && (
        <button onClick={handleBilling}>Manage Billing</button>
      )}

      {isFeatureActive('procurement_v2_enabled') && (
        <div className="new-feature-badge">Procurement V2 Active!</div>
      )}
    </div>
  );
}
```

### 3. Declarative UI Guarding

Use the `<Guard>` component to clean up conditional rendering blocks in your JSX:

```tsx
import { Guard } from '@/components/Guard';

export default function Toolbar() {
  return (
    <div className="flex gap-4">
      {/* Basic Permission check */}
      <Guard permission="po:create">
        <button>Create PO</button>
      </Guard>

      {/* Feature Flag check */}
      <Guard feature="procurement_v2_enabled">
        <span className="badge">Beta Features</span>
      </Guard>

      {/* Combined check with fallback rendering */}
      <Guard 
        permission="grn:approve" 
        feature="procurement_v2_enabled"
        fallback={<p className="text-gray-500">Upgrade your plan to approve GRNs</p>}
      >
        <button className="btn-primary">Approve Goods Received Note</button>
      </Guard>
    </div>
  );
}
```
