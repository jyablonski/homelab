import type { ReminderCategory } from "@/lib/schemas";

/**
 * Fields ReminderCard actually renders. Both the reminders CRUD `Reminder` shape
 * and the agenda/today `AgendaReminder` shape (different key names, no
 * completed_at/timestamps) satisfy this structurally.
 */
export type ReminderCardData = {
  id: number;
  reminder_type: string;
  reminder_message: string;
  reminder_start_date: string;
  reminder_end_date: string | null;
  is_completed: boolean;
};

export const reminderCategoryLabels: Record<ReminderCategory, string> = {
  car: "Car",
  house: "House",
  health: "Health",
  bill: "Bill",
  homelab: "Homelab",
  general: "General",
};

export function reminderCategoryLabel(category: string): string {
  return reminderCategoryLabels[category as ReminderCategory] ?? category;
}

type CategoryStyle = {
  /** Tailwind class for the small category dot shown on reminder rows. */
  dot: string;
  /** Tailwind classes applied when this category is the selected pill. */
  selected: string;
};

const reminderCategoryStyles: Record<ReminderCategory, CategoryStyle> = {
  car: {
    dot: "bg-blue-500",
    selected: "border-blue-500 bg-blue-500/10 text-blue-300",
  },
  house: {
    dot: "bg-green-500",
    selected: "border-green-500 bg-green-500/10 text-green-300",
  },
  health: {
    dot: "bg-rose-500",
    selected: "border-rose-500 bg-rose-500/10 text-rose-300",
  },
  bill: {
    dot: "bg-amber-500",
    selected: "border-amber-500 bg-amber-500/10 text-amber-300",
  },
  homelab: {
    dot: "bg-purple-500",
    selected: "border-purple-500 bg-purple-500/10 text-purple-300",
  },
  general: {
    dot: "bg-slate-400",
    selected: "border-slate-400 bg-slate-400/10 text-slate-300",
  },
};

const defaultCategoryStyle: CategoryStyle = {
  dot: "bg-slate-400",
  selected: "border-slate-400 bg-slate-400/10 text-slate-300",
};

export function reminderCategoryDotClass(category: string): string {
  return (reminderCategoryStyles[category as ReminderCategory] ?? defaultCategoryStyle)
    .dot;
}

export function reminderCategorySelectedClass(category: string): string {
  return (reminderCategoryStyles[category as ReminderCategory] ?? defaultCategoryStyle)
    .selected;
}
