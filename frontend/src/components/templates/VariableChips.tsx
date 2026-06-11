"use client";

import { User, Building2, Mail, Type } from "lucide-react";
import { TEMPLATE_VARIABLES } from "@/lib/template-builder";
import { cn } from "@/lib/utils";

const ICONS: Record<string, typeof User> = {
  name: User,
  first_name: User,
  last_name: Type,
  company: Building2,
  email: Mail,
};

interface VariableChipsProps {
  onInsert: (token: string) => void;
  className?: string;
}

export function VariableChips({ onInsert, className }: VariableChipsProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <p className="text-xs text-muted-foreground">
        Click to insert personalization into the field you are typing in:
      </p>
      <div className="flex flex-wrap gap-2">
        {TEMPLATE_VARIABLES.map((variable) => {
          const Icon = ICONS[variable.key] ?? User;
          return (
            <button
              key={variable.key}
              type="button"
              onClick={() => onInsert(`{{${variable.key}}}`)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50",
                "px-3 py-1.5 text-xs font-medium text-violet-700",
                "transition-colors hover:border-violet-300 hover:bg-violet-100"
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {variable.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
