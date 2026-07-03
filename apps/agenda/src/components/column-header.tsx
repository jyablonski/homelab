import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type ColumnHeaderProps = {
  label: string;
  dotClassName?: string;
  trailing?: ReactNode;
};

export function ColumnHeader({
  label,
  dotClassName = "bg-accent",
  trailing,
}: ColumnHeaderProps) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className={cn("h-1.5 w-1.5 rounded-full", dotClassName)} />
        <h2 className="text-xs font-semibold tracking-wide text-foreground uppercase">
          {label}
        </h2>
      </div>
      {trailing ? <div className="text-xs text-muted">{trailing}</div> : null}
    </div>
  );
}
