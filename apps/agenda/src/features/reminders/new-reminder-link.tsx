import { Plus } from "lucide-react";
import Link from "next/link";

export function NewReminderLink() {
  return (
    <Link
      href="/reminders/new"
      className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
    >
      <Plus className="h-4 w-4" />
      New reminder
    </Link>
  );
}
