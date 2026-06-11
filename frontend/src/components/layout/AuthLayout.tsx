import type { ReactNode } from "react";
import { ArrowUpRight, Shield, Sparkles, Zap } from "lucide-react";

interface AuthLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

const features = [
  { icon: Shield, text: "Compliance built into every send" },
  { icon: Zap, text: "Smart account rotation & tier caps" },
  { icon: Sparkles, text: "Preflight checks before launch" },
];

export function AuthLayout({
  children,
  title = "Welcome back",
  subtitle = "Sign in to your outreach workspace",
}: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen">
      {/* Editorial hero panel */}
      <div className="auth-mesh relative hidden w-[44%] flex-col justify-between overflow-hidden p-12 xl:p-16 lg:flex">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIj48ZmlsdGVyIGlkPSJhIiB4PSIwIiB5PSIwIj48ZmVUdXJidWxlbmNlIGJhc2VGcmVxdWVuY3k9Ii43NSIgc3RpdGNoVGlsZXM9InN0aXRjaCIgdHlwZT0iZnJhY3RhbE5vaXNlIi8+PGZlQ29sb3IgZGF0YS1ub2lzZT0iMC4wNSIvPjwvZmlsdGVyPjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWx0ZXI9InVybCgjYSkiIG9wYWNpdHk9IjAuNCIvPjwvc3ZnPg==')] opacity-30 mix-blend-overlay" />

        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium uppercase tracking-[0.2em] text-white/70 backdrop-blur-sm">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            Outreach Platform
          </div>
        </div>

        <div className="relative z-10 max-w-lg">
          <h1 className="font-display text-[3.25rem] leading-[1.05] tracking-tight text-white xl:text-[3.75rem]">
            Send with
            <br />
            <span className="italic text-white/90">precision</span>
            <span className="text-white/40"> & </span>
            <span className="bg-gradient-to-r from-violet-300 via-pink-300 to-amber-200 bg-clip-text text-transparent">
              poise.
            </span>
          </h1>
          <p className="mt-6 max-w-md text-base leading-relaxed text-white/50">
            OAuth-only Gmail outreach with deliverability guardrails, audit trails,
            and the polish your brand deserves.
          </p>
        </div>

        <ul className="relative z-10 space-y-4">
          {features.map(({ icon: Icon, text }) => (
            <li
              key={text}
              className="flex items-center gap-3 text-sm text-white/60"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-white/5">
                <Icon className="h-3.5 w-3.5 text-violet-300" strokeWidth={1.75} />
              </span>
              {text}
            </li>
          ))}
          <li className="pt-2">
            <a
              href="https://"
              onClick={(e) => e.preventDefault()}
              className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-widest text-white/40 transition-colors hover:text-white/70"
            >
              Trusted by growth teams
              <ArrowUpRight className="h-3 w-3" />
            </a>
          </li>
        </ul>
      </div>

      {/* Form panel */}
      <div className="relative flex w-full flex-col justify-center bg-[#FAF8F5] px-6 py-14 lg:w-[56%] lg:px-16 xl:px-24">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -right-20 top-0 h-72 w-72 rounded-full bg-violet-200/30 blur-3xl" />
          <div className="absolute -left-10 bottom-0 h-64 w-64 rounded-full bg-pink-200/25 blur-3xl" />
        </div>

        <div className="relative mx-auto w-full max-w-[420px] animate-slide-up">
          <div className="mb-10 lg:hidden">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">
              Outreach
            </p>
            <h2 className="font-display mt-3 text-3xl text-foreground">{title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
          </div>

          <div className="mb-8 hidden lg:block">
            <h2 className="font-display text-4xl tracking-tight text-foreground">
              {title}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}
