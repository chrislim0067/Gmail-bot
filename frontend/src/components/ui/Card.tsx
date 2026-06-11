import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

export function Card({
  className,
  children,
  hover = false,
  glass = false,
  ...props
}: HTMLAttributes<HTMLDivElement> & { hover?: boolean; glass?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border-subtle bg-white/90 shadow-soft",
        glass && "glass-card",
        hover && "transition-all duration-300 hover:-translate-y-0.5 hover:shadow-float hover:border-violet-100",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("border-b border-border-subtle/80 px-6 py-5", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardTitle({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn("text-sm font-semibold tracking-tight text-foreground", className)}
      {...props}
    >
      {children}
    </h3>
  );
}

export function CardDescription({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn("mt-1 text-sm leading-relaxed text-muted-foreground", className)} {...props}>
      {children}
    </p>
  );
}

export function CardContent({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-6 py-5", className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 border-t border-border-subtle/80 px-6 py-5",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function DataCard({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <Card className={cn("overflow-hidden", className)} hover {...props}>
      {children}
    </Card>
  );
}
