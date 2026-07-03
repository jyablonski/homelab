import type { ReactNode } from "react";

import { NavLink } from "@/components/nav-link";
import { getReminderCounts } from "@/features/reminders/reminder-counts";

export async function AppShell({ children }: { children: ReactNode }) {
  const counts = await getReminderCounts();

  return (
    <div className="flex min-h-full">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-sidebar-background">
        <div className="flex items-center gap-2 px-4 py-5">
          <span className="h-6 w-6 rounded-md bg-accent" />
          <span className="text-sm font-semibold tracking-tight">Agenda</span>
        </div>

        <nav className="flex flex-col gap-0.5 px-2">
          <NavLink href="/">Today</NavLink>
          <NavLink href="/upcoming" count={counts?.upcoming}>
            Upcoming
          </NavLink>
          <NavLink href="/completed" count={counts?.completed}>
            Completed
          </NavLink>
        </nav>

        <div className="mt-auto flex items-center gap-2 border-t border-border px-4 py-4">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted-background text-xs font-medium text-muted">
            HL
          </span>
          <div className="flex flex-col leading-tight">
            <span className="text-sm text-foreground">Home</span>
            <span className="text-xs text-muted">agenda.home</span>
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-x-hidden px-8 py-6">{children}</main>
    </div>
  );
}
