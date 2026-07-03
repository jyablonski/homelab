"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api/client";
import {
  completeReminder,
  createReminder,
  reopenReminder,
  updateReminder,
} from "@/lib/api/reminders";
import { reminderCreateSchema, reminderUpdateSchema } from "@/lib/schemas";

export type ReminderFormState = { error?: string };

function revalidateReminderPaths() {
  revalidatePath("/");
  revalidatePath("/upcoming");
  revalidatePath("/completed");
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function formValue(formData: FormData, key: string): string | null {
  const value = formData.get(key);
  return typeof value === "string" && value.length > 0 ? value : null;
}

export async function createReminderAction(
  _prevState: ReminderFormState,
  formData: FormData,
): Promise<ReminderFormState> {
  const parsed = reminderCreateSchema.safeParse({
    reminder_type: formValue(formData, "reminder_type"),
    reminder_message: formValue(formData, "reminder_message"),
    reminder_start_date: formValue(formData, "reminder_start_date"),
    reminder_end_date: formValue(formData, "reminder_end_date"),
  });

  if (!parsed.success) {
    return { error: "Please fill in category, message, and start date." };
  }

  try {
    await createReminder(parsed.data);
  } catch (error) {
    return { error: errorMessage(error, "Failed to create reminder.") };
  }

  revalidateReminderPaths();
  redirect("/");
}

export async function updateReminderAction(
  id: number,
  _prevState: ReminderFormState,
  formData: FormData,
): Promise<ReminderFormState> {
  const parsed = reminderUpdateSchema.safeParse({
    reminder_type: formValue(formData, "reminder_type"),
    reminder_message: formValue(formData, "reminder_message"),
    reminder_start_date: formValue(formData, "reminder_start_date"),
    reminder_end_date: formValue(formData, "reminder_end_date"),
  });

  if (!parsed.success) {
    return { error: "Please fill in category, message, and start date." };
  }

  try {
    await updateReminder(id, parsed.data);
  } catch (error) {
    return { error: errorMessage(error, "Failed to update reminder.") };
  }

  revalidateReminderPaths();
  redirect("/");
}

export async function completeReminderAction(id: number): Promise<void> {
  await completeReminder(id);
  revalidateReminderPaths();
}

export async function reopenReminderAction(id: number): Promise<void> {
  await reopenReminder(id);
  revalidateReminderPaths();
}
