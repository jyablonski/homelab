"use client";

import { useActionState } from "react";
import Link from "next/link";

import { Button } from "@/components/button";
import { Callout } from "@/components/callout";
import { Field } from "@/components/field";
import type { Reminder } from "@/lib/schemas";

import { CategoryPicker } from "@/features/reminders/category-picker";
import {
  completeReminderAction,
  createReminderAction,
  reopenReminderAction,
  type ReminderFormState,
  updateReminderAction,
} from "@/features/reminders/reminder-actions";

const initialState: ReminderFormState = {};

const inputClass =
  "rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent";

export function ReminderForm({ reminder }: { reminder?: Reminder }) {
  const action = reminder
    ? updateReminderAction.bind(null, reminder.id)
    : createReminderAction;
  const [state, formAction, pending] = useActionState(action, initialState);
  const toggleAction = reminder
    ? reminder.is_completed
      ? reopenReminderAction.bind(null, reminder.id)
      : completeReminderAction.bind(null, reminder.id)
    : null;

  return (
    <div className="mx-auto max-w-xl">
      <Link
        href="/"
        className="mb-6 inline-block text-sm text-muted transition-colors hover:text-foreground"
      >
        ← Back to today
      </Link>

      <h1 className="text-xl font-semibold text-foreground">
        {reminder ? "Edit reminder" : "New reminder"}
      </h1>
      <p className="mt-1 text-sm text-muted">
        {reminder
          ? "Update the message or reschedule the next reminder date."
          : "Record what happened, then choose when you want to be reminded."}
      </p>

      <form action={formAction} className="mt-6 flex flex-col gap-5">
        <Field label="Category" htmlFor="reminder_type">
          <CategoryPicker
            name="reminder_type"
            defaultValue={reminder?.reminder_type ?? "general"}
          />
        </Field>

        <Field label="Message" htmlFor="reminder_message">
          <textarea
            id="reminder_message"
            name="reminder_message"
            required
            rows={3}
            placeholder="e.g. Get oil changed soon"
            defaultValue={reminder?.reminder_message}
            className={inputClass}
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Reminder date" htmlFor="reminder_start_date">
            <input
              id="reminder_start_date"
              name="reminder_start_date"
              type="date"
              required
              defaultValue={reminder?.reminder_start_date}
              className={inputClass}
            />
          </Field>

          <Field label="End date" htmlFor="reminder_end_date" hint="Optional">
            <input
              id="reminder_end_date"
              name="reminder_end_date"
              type="date"
              defaultValue={reminder?.reminder_end_date ?? undefined}
              className={inputClass}
            />
          </Field>
        </div>

        <Callout>
          No recurrence needed — log what happened, then set the next date. e.g.{" "}
          <span className="italic">&ldquo;Oil change completed Jun 1, 2025&rdquo;</span>{" "}
          with a reminder on <span className="font-medium">Jun 1, 2026</span>.
        </Callout>

        {state.error ? <p className="text-sm text-danger">{state.error}</p> : null}

        <div className="flex items-center justify-end gap-3 border-t border-border pt-4">
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted-background"
          >
            Cancel
          </Link>
          <Button type="submit" disabled={pending}>
            {pending ? "Saving..." : reminder ? "Save changes" : "Save reminder"}
          </Button>
        </div>
      </form>

      {reminder && toggleAction ? (
        <div className="mt-6 flex items-center gap-3 border-t border-border pt-4">
          <span className="text-xs text-muted">Status:</span>
          <form action={toggleAction}>
            <Button type="submit" variant="secondary">
              {reminder.is_completed ? "Reopen" : "Mark complete"}
            </Button>
          </form>
        </div>
      ) : null}
    </div>
  );
}
