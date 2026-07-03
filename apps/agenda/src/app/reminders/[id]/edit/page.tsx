import { notFound } from "next/navigation";

import { ApiError } from "@/lib/api/client";
import { getReminder } from "@/lib/api/reminders";

import { ReminderForm } from "@/features/reminders/reminder-form";

// The agenda API is only reachable from inside the cluster, so this must
// never be attempted at build time — always render at request time.
export const dynamic = "force-dynamic";

export default async function EditReminderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const reminderId = Number(id);

  if (!Number.isInteger(reminderId)) {
    notFound();
  }

  let reminder;
  try {
    reminder = await getReminder(reminderId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return <ReminderForm reminder={reminder} />;
}
