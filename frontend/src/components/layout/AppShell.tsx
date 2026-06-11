"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { getCurrentUser, isAuthenticated } from "@/lib/auth";
import type { User } from "@/types/api";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const isAuthPage = pathname === "/login" || pathname === "/register";
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!isAuthPage);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (isAuthPage) {
      setLoading(false);
      return;
    }

    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    getCurrentUser()
      .then((currentUser) => {
        if (!currentUser) {
          router.replace("/login");
        } else {
          setUser(currentUser);
        }
      })
      .finally(() => setLoading(false));
  }, [isAuthPage, router, pathname]);

  if (isAuthPage) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="app-canvas flex min-h-screen items-center justify-center">
        <LoadingSpinner size="lg" label="Loading workspace…" />
      </div>
    );
  }

  return (
    <div className="app-canvas min-h-screen">
      <Sidebar
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
      />
      <div className="lg:pl-sidebar">
        <TopBar user={user} onMenuClick={() => setMobileNavOpen(true)} />
        <main className="page-container animate-fade-in">{children}</main>
      </div>
    </div>
  );
}
