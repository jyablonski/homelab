import { Info } from "lucide-react";
import type { ReactNode } from "react";

export function Callout({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-2 rounded-lg border border-accent/30 bg-accent/10 p-3 text-sm text-foreground">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
      <div>{children}</div>
    </div>
  );
}
