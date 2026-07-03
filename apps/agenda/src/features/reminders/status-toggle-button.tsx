"use client";

import { Check } from "lucide-react";
import { useFormStatus } from "react-dom";

import { cn } from "@/lib/cn";

export function StatusToggleButton({ isCompleted }: { isCompleted: boolean }) {
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      aria-label={isCompleted ? "Reopen reminder" : "Mark reminder complete"}
      title={isCompleted ? "Reopen" : "Mark complete"}
      className={cn(
        "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        isCompleted
          ? "border-success bg-success/20 text-success"
          : "border-muted text-transparent hover:border-accent",
      )}
    >
      <Check className="h-3.5 w-3.5" strokeWidth={3} />
    </button>
  );
}
