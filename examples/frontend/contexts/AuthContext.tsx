import React, { createContext, useContext, useEffect, useState } from "react";

import { AuthContextResponse, fetchAuthContext, Role } from "../lib/api";

interface AuthContextType {
  role: Role | null;
  permissions: string[];
  features: string[];
  isLoading: boolean;
  error: Error | null;
  hasPermission: (code: string) => boolean;
  isFeatureActive: (name: string) => boolean;
  refetch: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({
  children,
  apiBaseUrl,
  tenantId,
  token,
}: {
  children: React.ReactNode;
  apiBaseUrl: string;
  tenantId: string;
  token: string;
}) {
  const [state, setState] = useState<AuthContextResponse>({
    role: null,
    permissions: [],
    features: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadContext = async () => {
    if (!tenantId || !token) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchAuthContext(apiBaseUrl, tenantId, token);
      setState(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadContext();
  }, [apiBaseUrl, tenantId, token]);

  const hasPermission = (code: string) => {
    return state.permissions.includes(code);
  };

  const isFeatureActive = (name: string) => {
    return state.features.includes(name);
  };

  return (
    <AuthContext.Provider
      value={{
        role: state.role,
        permissions: state.permissions,
        features: state.features,
        isLoading,
        error,
        hasPermission,
        isFeatureActive,
        refetch: loadContext,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
