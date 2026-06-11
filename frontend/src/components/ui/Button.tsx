import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

const variants = {
  primary: "btn-gradient rounded-full font-semibold disabled:opacity-50",
  secondary:
    "rounded-full bg-stone-900/5 text-foreground hover:bg-stone-900/10 font-medium disabled:opacity-50",
  ghost:
    "rounded-xl text-muted-foreground hover:bg-stone-900/5 hover:text-foreground disabled:opacity-50",
  danger:
    "rounded-full bg-danger text-white shadow-soft hover:bg-red-700 font-semibold disabled:opacity-50",
  outline:
    "rounded-full border border-border bg-white/80 text-foreground shadow-soft hover:border-violet-200 hover:bg-violet-50/50 font-medium disabled:opacity-50",
};

const sizes = {
  sm: "h-8 gap-1.5 px-4 text-xs",
  md: "h-10 gap-2 px-5 text-sm",
  lg: "h-12 gap-2 px-7 text-sm",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading,
      disabled,
      children,
      ...props
    },
    ref
  ) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/40 focus-visible:ring-offset-2",
        "active:scale-[0.98] disabled:active:scale-100",
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  )
);

Button.displayName = "Button";
