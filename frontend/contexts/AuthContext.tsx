"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";

const AuthContext = createContext(null);

// User roles
export const USER_ROLES = {
  ADMIN: "admin",
  USER: "user",
  VIEWER: "viewer",
};

function mapSupabaseUser(user) {
  if (!user) return null;
  const metadata = user.user_metadata || {};

  return {
    id: user.id,
    name: metadata.name || user.email?.split("@")[0] || "User",
    email: user.email,
    company: metadata.company || "",
    role: metadata.role || USER_ROLES.USER,
    createdAt: user.created_at,
  };
}

async function fetchJson(url, options) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshSession = useCallback(async () => {
    try {
      const data = await fetchJson("/api/auth/session", { method: "GET" });
      setUser(mapSupabaseUser(data.user));
      setToken(data.accessToken || null);
    } catch {
      setUser(null);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  // Login function
  const login = useCallback(async (email, password) => {
    try {
      await fetchJson("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      await refreshSession();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message || "Login failed" };
    }
  }, [refreshSession]);

  // Signup function
  const signup = useCallback(async (name, email, password, company) => {
    try {
      await fetchJson("/api/auth/signup", {
        method: "POST",
        body: JSON.stringify({ name, email, password, company }),
      });

      await refreshSession();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message || "Signup failed" };
    }
  }, [refreshSession]);

  // Logout function
  const logout = useCallback(async () => {
    try {
      await fetchJson("/api/auth/logout", { method: "POST" });
    } finally {
      setToken(null);
      setUser(null);
    }
  }, []);

  const requestPasswordReset = useCallback(async (email) => {
    try {
      await fetchJson("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });

      return { success: true };
    } catch (error) {
      return { success: false, error: error.message || "Failed to request password reset" };
    }
  }, []);

  const resetPassword = useCallback(async (_resetToken, newPassword) => {
    try {
      await fetchJson("/api/auth/update-password", {
        method: "POST",
        body: JSON.stringify({ password: newPassword }),
      });

      return { success: true };
    } catch (error) {
      return { success: false, error: error.message || "Failed to reset password" };
    }
  }, []);

  // Check if user owns a resource
  const isOwner = useCallback(
    (resourceOwnerId) => {
      return user && user.id === resourceOwnerId;
    },
    [user]
  );

  // Check if user has specific role
  const hasRole = useCallback(
    (requiredRole) => {
      if (!user) return false;
      if (user.role === USER_ROLES.ADMIN) return true; // Admin has all permissions
      return user.role === requiredRole;
    },
    [user]
  );

  // Check if user can edit (owner or admin)
  const canEdit = useCallback(
    (resourceOwnerId) => {
      if (!user) return false;
      if (user.role === USER_ROLES.ADMIN) return true;
      return user.id === resourceOwnerId;
    },
    [user]
  );

  // Check if user can delete (owner or admin)
  const canDelete = useCallback(
    (resourceOwnerId) => {
      if (!user) return false;
      if (user.role === USER_ROLES.ADMIN) return true;
      return user.id === resourceOwnerId;
    },
    [user]
  );

  // Check if user can create resources
  const canCreate = useCallback(() => {
    if (!user) return false;
    return user.role === USER_ROLES.ADMIN || user.role === USER_ROLES.USER;
  }, [user]);

  // Get auth headers for API calls
  const getAuthHeader = useCallback(() => {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [token]);

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user,
    login,
    signup,
    logout,
    requestPasswordReset,
    resetPassword,
    isOwner,
    hasRole,
    canEdit,
    canDelete,
    canCreate,
    getAuthHeader,
    USER_ROLES,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
