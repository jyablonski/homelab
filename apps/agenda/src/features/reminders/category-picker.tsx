"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";

import {
  reminderCategoryDotClass,
  reminderCategoryLabels,
  reminderCategorySelectedClass,
} from "@/features/reminders/types";

type CategoryPickerProps = {
  name: string;
  defaultValue: string;
};

export function CategoryPicker({ name, defaultValue }: CategoryPickerProps) {
  const [selected, setSelected] = useState(defaultValue);

  return (
    <div className="flex flex-wrap gap-2">
      <input type="hidden" id={name} name={name} value={selected} />
      {Object.entries(reminderCategoryLabels).map(([value, label]) => {
        const isSelected = value === selected;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setSelected(value)}
            aria-pressed={isSelected}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors",
              isSelected
                ? reminderCategorySelectedClass(value)
                : "border-border text-muted hover:text-foreground",
            )}
          >
            <span
              className={cn("h-1.5 w-1.5 rounded-full", reminderCategoryDotClass(value))}
            />
            {label}
          </button>
        );
      })}
    </div>
  );
}
