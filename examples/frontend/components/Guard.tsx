import React from "react";

import { useAuth } from "../contexts/AuthContext";

interface GuardProps {
  children: React.ReactNode;
  permission?: string;
  feature?: string;
  fallback?: React.ReactNode;
}

/**
 * Conditional rendering guard component.
 *
 * Only renders children if the specified feature is active and the user
 * holds the specified permission code in the current tenant.
 */
export function Guard({
  children,
  permission,
  feature,
  fallback = null,
}: GuardProps) {
  const { hasPermission, isFeatureActive, isLoading } = useAuth();

  if (isLoading) {
    return null; // Or a skeleton placeholder/spinner
  }

  if (feature && !isFeatureActive(feature)) {
    return <>{fallback}</>;
  }

  if (permission && !hasPermission(permission)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
