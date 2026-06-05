# Dynamic RBAC & Feature Control System (Internship Assignment)

A lightweight, multi-tenant Django + Django REST Framework (DRF) backend implementation of a dynamic **Role-Based Access Control (RBAC)** engine, **Feature Controls**, and a signal-driven **Audit Logging** system.

This project is built using a clean **Service Layer** pattern to isolate core business rules from HTTP translation logic.

---

## 📋 Assignment Requirements & Solutions

### 1. Multi-Organization / Multi-Tenancy
- **Shared-Database Isolation**: Each organization (tenant) is isolated dynamically. Subdomains are mapped to their corresponding workspace workspace automatically using a custom middleware.
- **Auto-Seeded Roles**: When a new organization registers, a default set of system roles (`owner`, `admin`, `member`) are seeded with pre-configured permissions.

### 2. Dynamic RBAC System
- **Atomic Permissions**: Scoped capabilities registered globally (e.g., `po:create`, `grn:approve`).
- **Dynamic Tenant Roles**: Organizations can define new custom roles dynamically (e.g. "Procurement Manager") via views/serializers and bind them to any array of permissions.
- **Hierarchy Weights**: Roles carry a numeric weight to allow simple hierarchy checks (e.g. checking if a user is *at least* an administrator).

### 3. Feature Controls (On / Off)
- **Tenant-Scoped Toggles**: Features can be toggled on/off globally (`tenant=None`) or overridden specifically for individual organizations.
- **DRF Integration**: A unified `IsTenantAuthorized` permission class validates both the feature flag gate and the user's role permission capability at the endpoint layer.

### 4. Basic Audit Logs
- **Activity Tracking**: Records login events, permission additions, and changes.
- **Delta History ("Who changed what")**: Captures field-level changes (comparing state before and after updates) and logs them into a database JSON field.
- **Async Execution**: The logging payload creation and database insertions are processed asynchronously off the request-response thread using Celery.

---

## 🛠 Tech Stack
- **Backend**: Python 3.12, Django 5.x, Django REST Framework (DRF).
- **Database**: SQLite (SQL engine configured for local-only service-free development).
- **Queue/Workers**: Celery (configured in synchronous execution for local setup).
- **Frontend Integration**: Next.js (TypeScript helpers, AuthContext providers, and declarative `<Guard>` wrapper examples included).

---

## 🚀 Quickstart & Setup

### 1. Install Dependencies
Set up your virtual environment and install the unified dependencies list:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy the default environment template:
```bash
cp .env.example .env
```

### 3. Database Setup & Migrations
Run the migrations to create the SQLite tables and apply dynamic RBAC schemas:
```bash
python manage.py migrate
```

### 4. Seed Demo Tenant & Workspace Data
Seed the local database with dummy organizations, users, default roles, and permissions:
```bash
python manage.py seed_demo
```
This boots up two demo organizations:
- **Tenant One**: `tenant1` (`00000000-0000-4000-8000-000000000001`)
- **Tenant Two**: `tenant2` (`00000000-0000-4000-8000-000000000002`)

It also registers a default administrator account:
- **Username**: `admin@tenant1.localhost`
- **Password**: `password123`

### 5. Boot Dev Server
Start the local server:
```bash
python manage.py runserver
```
Once running, interactive API documentation is available at **`http://localhost:8000/api/docs/`**.

---

## 🧪 Running the Verification Suite
Run pytest to verify all **277 unit, service, and integration tests**:
```bash
pytest
```

---

## 💡 Frontend Integration (Next.js Example)
Use the declarative `<Guard>` wrapper in your Next.js React UI to hide or show components based on active feature toggles and RBAC permissions:
```tsx
import { Guard } from '@/components/Guard';

export default function ActionButton() {
  return (
    <Guard permission="po:create" feature="procurement_v2_enabled">
      <button className="btn-primary">Create Purchase Order</button>
    </Guard>
  );
}
```
*Read the full [Frontend Integration Guide](examples/frontend/README.md) for custom hooks and auth context setup.*
