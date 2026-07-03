import { PageHeader } from "@/components/page-header";
import { groupReminders, listReminders } from "@/lib/api/reminders";

import { AgendaSection } from "@/features/agenda/agenda-section";
import { NewReminderLink } from "@/features/reminders/new-reminder-link";
import { ReminderList } from "@/features/reminders/reminder-list";

// The agenda API is only reachable from inside the cluster, so this must
// never be attempted at build time — always render at request time.
export const dynamic = "force-dynamic";

export default async function UpcomingPage() {
  const reminders = await listReminders({ includeCompleted: false });
  const { dueSoon, upcoming } = groupReminders(reminders);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title="Upcoming" action={<NewReminderLink />} />

      <AgendaSection title="Due soon" count={dueSoon.length}>
        <ReminderList
          reminders={dueSoon}
          groupByDate
          emptyTitle="Nothing due in the next week"
        />
      </AgendaSection>

      <AgendaSection title="Later" count={upcoming.length}>
        <ReminderList
          reminders={upcoming}
          groupByDate
          emptyTitle="No reminders further out"
        />
      </AgendaSection>
    </div>
  );
}
