"use client";

import { Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import type { User } from "@/types/api";

interface TopBarProps {
  user: User | null;
  onMenuClick?: () => void;
  title?: string;
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function TopBar({ user, onMenuClick, title }: TopBarProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-white/40 bg-white/60 backdrop-blur-xl">
      <div className="flex h-[4.25rem] items-center justify-between gap-4 px-4 sm:px-8 lg:px-10">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className={cn(
              "inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border-subtle bg-white/80 text-muted-foreground shadow-soft transition-all hover:text-foreground lg:hidden"
            )}
            aria-label="Open navigation"
          >
            <Menu className="h-4 w-4" />
          </button>
          {title && (
            <p className="truncate text-sm font-medium text-muted-foreground lg:hidden">
              {title}
            </p>
          )}
        </div>

        {user && (
          <div className="flex items-center gap-4">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-foreground">{user.full_name}</p>
              <p className="text-xs text-muted-foreground">{user.email}</p>
            </div>
            <div
              className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-pink-500 text-xs font-bold text-white shadow-md shadow-violet-500/25 ring-2 ring-white"
              title={user.email}
            >
              {initials(user.full_name || user.email)}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
