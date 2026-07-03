import type { ReactNode } from "react";

type AgendaSectionProps = {
  title: string;
  count: number;
  children: ReactNode;
};

export function AgendaSection({ title, count, children }: AgendaSectionProps) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        <span className="rounded-full bg-muted-background px-2 py-0.5 text-xs text-muted">
          {count}
        </span>
      </div>
      {children}
    </section>
  );
}
