import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  variant?: "default" | "plain";
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, variant = "default", id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="mb-2 block text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            "flex h-12 w-full rounded-xl border border-border bg-white/90 px-4 py-2 text-sm text-foreground shadow-soft",
            "placeholder:text-stone-400 transition-all duration-200",
            "focus:border-violet-300 focus:outline-none focus:ring-4 focus:ring-violet-500/10",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-danger focus:border-danger focus:ring-danger/10",
            className
          )}
          {...props}
        />
        {hint && !error && (
          <p className="mt-2 text-xs text-muted-foreground">{hint}</p>
        )}
        {error && <p className="mt-2 text-xs text-danger">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  variant?: "default" | "plain";
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, hint, variant = "default", id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="mb-2 block text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          className={cn(
            "flex min-h-[140px] w-full rounded-xl border border-border bg-white/90 px-4 py-3 text-sm text-foreground shadow-soft",
            "placeholder:text-stone-400 transition-all",
            variant === "plain" ? "leading-relaxed" : "font-mono text-[13px]",
            "focus:border-violet-300 focus:outline-none focus:ring-4 focus:ring-violet-500/10",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-danger focus:border-danger focus:ring-danger/10",
            className
          )}
          {...props}
        />
        {hint && !error && (
          <p className="mt-2 text-xs text-muted-foreground">{hint}</p>
        )}
        {error && <p className="mt-2 text-xs text-danger">{error}</p>}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
