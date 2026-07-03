import { ColumnHeader } from "@/components/column-header";
import { DueSoonPanel } from "@/features/reminders/due-soon-panel";
import { ReminderList } from "@/features/reminders/reminder-list";
import type { ReminderCardData } from "@/features/reminders/types";

type RemindersColumnProps = {
  active: ReminderCardData[];
  dueSoon: ReminderCardData[];
};

export function RemindersColumn({ active, dueSoon }: RemindersColumnProps) {
  return (
    <div className="flex flex-col gap-4">
      <ColumnHeader label="Reminders" dotClassName="bg-warning" />

      <DueSoonPanel reminders={dueSoon} />

      <div>
        <div className="mb-1 flex items-center gap-2 px-2">
          <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">
            Active
          </h3>
          <span className="text-xs text-muted">{active.length}</span>
        </div>
        <ReminderList reminders={active} emptyTitle="Nothing active today" />
      </div>
    </div>
  );
}
