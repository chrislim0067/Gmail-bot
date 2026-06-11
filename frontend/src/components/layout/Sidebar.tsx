"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  ClipboardList,
  FileText,
  Inbox,
  LayoutDashboard,
  Layers,
  LogOut,
  Mail,
  Megaphone,
  Send,
  Settings,
  Shield,
  ShieldAlert,
  UserCheck,
  Users,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { logout } from "@/lib/auth";

const navSections = [
  {
    label: "Overview",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
    ],
  },
  {
    label: "Gmail",
    items: [
      { href: "/accounts", label: "Gmail Accounts", icon: Mail },
      { href: "/accounts/connect", label: "Connect Gmail", icon: UserCheck },
      { href: "/accounts/review", label: "Review Queue", icon: ShieldAlert },
      { href: "/account-pools", label: "Account Pools", icon: Layers },
      { href: "/health", label: "Account Health", icon: Activity },
    ],
  },
  {
    label: "Outreach",
    items: [
      { href: "/campaigns", label: "Campaigns", icon: Megaphone },
      { href: "/templates", label: "Outreach content", icon: FileText },
      { href: "/queue", label: "Send Queue", icon: Send },
      { href: "/replies", label: "Replies", icon: Inbox },
      { href: "/unsubscribes", label: "Unsubscribes", icon: Users },
    ],
  },
  {
    label: "Compliance",
    items: [
      { href: "/risk", label: "Risk Budget", icon: Shield },
      { href: "/audit-logs", label: "Audit Logs", icon: ClipboardList },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ mobileOpen = false, onMobileClose }: SidebarProps) {
  const pathname = usePathname();

  async function handleLogout() {
    await logout();
    window.location.href = "/login";
  }

  function isActive(href: string) {
    return href === "/"
      ? pathname === "/"
      : pathname === href || pathname.startsWith(`${href}/`);
  }

  const navContent = (
    <>
      <div className="flex h-[4.25rem] items-center justify-between gap-3 border-b border-white/[0.06] px-5">
        <div className="flex items-center gap-3">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 via-pink-500 to-amber-400 shadow-lg shadow-violet-500/20">
            <Send className="h-4 w-4 text-white" strokeWidth={2.25} />
          </div>
          <div>
            <p className="font-display text-lg leading-none text-white">Outreach</p>
            <p className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-white/35">
              Gmail
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onMobileClose}
          className="rounded-lg p-1.5 text-white/40 hover:bg-white/5 hover:text-white lg:hidden"
          aria-label="Close navigation"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5 scrollbar-thin">
        {navSections.map((section) => (
          <div key={section.label} className="mb-6 last:mb-0">
            <p className="mb-2.5 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/25">
              {section.label}
            </p>
            <ul className="space-y-1">
              {section.items.map(({ href, label, icon: Icon }) => {
                const active = isActive(href);
                return (
                  <li key={href}>
                    <Link
                      href={href}
                      onClick={onMobileClose}
                      className={cn(
                        "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all duration-200",
                        active
                          ? "nav-active-glow text-white"
                          : "text-white/45 hover:bg-white/[0.04] hover:text-white/80"
                      )}
                    >
                      <Icon
                        className={cn(
                          "h-[18px] w-[18px] shrink-0 transition-colors",
                          active
                            ? "text-violet-300"
                            : "text-white/30 group-hover:text-white/55"
                        )}
                        strokeWidth={active ? 2.25 : 1.75}
                      />
                      {label}
                      {active && (
                        <span className="ml-auto h-1.5 w-1.5 rounded-full bg-gradient-to-r from-violet-400 to-pink-400" />
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-white/[0.06] p-3">
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium text-white/40 transition-colors hover:bg-white/[0.04] hover:text-white/70"
        >
          <LogOut className="h-[18px] w-[18px]" strokeWidth={1.75} />
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onMobileClose}
          aria-label="Close menu overlay"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-sidebar flex-col border-r border-white/[0.04] bg-[#0a0a0a] text-white shadow-float transition-transform duration-300 ease-out lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {navContent}
      </aside>
    </>
  );
}
