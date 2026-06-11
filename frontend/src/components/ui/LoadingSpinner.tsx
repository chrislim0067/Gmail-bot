import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  label?: string;
}

const sizes = {
  sm: "h-5 w-5 border-[1.5px]",
  md: "h-8 w-8 border-2",
  lg: "h-10 w-10 border-2",
};

export function LoadingSpinner({
  className,
  size = "md",
  label = "Loading",
}: LoadingSpinnerProps) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3", className)}
      role="status"
      aria-label={label}
    >
      <div
        className={cn(
          "animate-spin rounded-full border-violet-500 border-t-transparent",
          sizes[size]
        )}
      />
      {size === "lg" && (
        <p className="text-sm text-muted-foreground">{label}</p>
      )}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex min-h-[280px] items-center justify-center">
      <LoadingSpinner size="md" />
    </div>
  );
}
