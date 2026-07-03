import { PageHeader } from "@/components/page-header";
import { getTodayAgenda } from "@/lib/api/agenda";
import { formatWeekdayDate } from "@/lib/dates";

import { AgendaList } from "@/features/agenda/agenda-list";
import { NewReminderLink } from "@/features/reminders/new-reminder-link";

// The agenda API is only reachable from inside the cluster, so this must
// never be attempted at build time — always render at request time.
export const dynamic = "force-dynamic";

export default async function TodayPage() {
  const agenda = await getTodayAgenda();
  const stats = [
    `${agenda.reminders.active.length} active`,
    `${agenda.reminders.due_soon.length} due soon`,
    `${agenda.events.length} events`,
  ].join(" · ");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={formatWeekdayDate()}
        subtitle={stats}
        action={<NewReminderLink />}
      />
      <AgendaList agenda={agenda} />
    </div>
  );
}
