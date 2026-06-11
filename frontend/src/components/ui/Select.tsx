import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, hint, id, children, ...props }, ref) => {
    const selectId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="mb-2 block text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground"
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={cn(
            "flex h-12 w-full appearance-none rounded-xl border border-border bg-white/90 px-4 py-2 text-sm text-foreground shadow-soft transition-all duration-200",
            "focus:border-violet-300 focus:outline-none focus:ring-4 focus:ring-violet-500/10",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-danger focus:border-danger focus:ring-danger/10",
            className
          )}
          {...props}
        >
          {children}
        </select>
        {hint && !error && (
          <p className="mt-2 text-xs text-muted-foreground">{hint}</p>
        )}
        {error && <p className="mt-2 text-xs text-danger">{error}</p>}
      </div>
    );
  }
);

Select.displayName = "Select";
