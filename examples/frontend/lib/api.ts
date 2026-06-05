export interface Role {
  id: string;
  name: string;
  slug: string;
  weight: number;
}

export interface AuthContextResponse {
  role: Role | null;
  permissions: string[];
  features: string[];
}

/**
 * Fetch permissions, roles, and feature flags for the current user in a tenant.
 */
export async function fetchAuthContext(
  apiBaseUrl: string,
  tenantId: string,
  token: string
): Promise<AuthContextResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/rbac/${tenantId}/me/`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch auth context: ${response.statusText}`);
  }

  return response.json();
}
