import { PageHeader } from "@/components/page-header";
import { listReminders } from "@/lib/api/reminders";

import { NewReminderLink } from "@/features/reminders/new-reminder-link";
import { ReminderList } from "@/features/reminders/reminder-list";

// The agenda API is only reachable from inside the cluster, so this must
// never be attempted at build time — always render at request time.
export const dynamic = "force-dynamic";

export default async function CompletedPage() {
  const reminders = await listReminders({ includeCompleted: true });
  const completed = reminders
    .filter((reminder) => reminder.is_completed)
    .sort((a, b) => (b.completed_at ?? "").localeCompare(a.completed_at ?? ""));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Completed" action={<NewReminderLink />} />
      <ReminderList
        reminders={completed}
        emptyTitle="No completed reminders yet"
      />
    </div>
  );
}
