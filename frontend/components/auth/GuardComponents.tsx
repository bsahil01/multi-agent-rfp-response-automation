"use client";

import { ReactNode } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Lock, AlertCircle } from "lucide-react";
import Link from "next/link";

interface GuestOnlyProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function GuestOnly({ children, fallback }: GuestOnlyProps) {
  const { isGuest } = useAuth();
  
  if (isGuest) {
    return <>{children}</>;
  }
  
  return <>{fallback || null}</>;
}

interface AuthenticatedOnlyProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function AuthenticatedOnly({ children, fallback }: AuthenticatedOnlyProps) {
  const { isAuthenticated, isGuest } = useAuth();
  
  if (isAuthenticated && !isGuest) {
    return <>{children}</>;
  }
  
  return <>{fallback || null}</>;
}

interface GuestOverlayProps {
  children: ReactNode;
  message?: string;
}

export function GuestOverlay({ children, message = "Please sign in to access this feature" }: GuestOverlayProps) {
  const { isGuest } = useAuth();
  
  if (!isGuest) {
    return <>{children}</>;
  }
  
  return (
    <div className="relative">
      <div className="opacity-50 pointer-events-none">
        {children}
      </div>
      <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm rounded-lg border border-border">
        <div className="text-center p-6 max-w-sm">
          <Lock className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-foreground mb-2">
            Guest Mode
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            {message}
          </p>
          <div className="space-y-2">
            <Link href="/login">
              <Button className="w-full">
                Sign In to Access
              </Button>
            </Link>
            <Link href="/signup">
              <Button variant="outline" className="w-full">
                Create Account
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

interface GuestBadgeProps {
  className?: string;
}

export function GuestBadge({ className }: GuestBadgeProps) {
  const { isGuest } = useAuth();
  
  if (!isGuest) return null;
  
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 bg-secondary border border-border rounded-full text-sm ${className}`}>
      <AlertCircle className="w-4 h-4 text-muted-foreground" />
      <span className="text-muted-foreground">Guest Mode</span>
    </div>
  );
}
