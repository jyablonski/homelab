import { cn } from "@/lib/cn";

type StatusTone = "neutral" | "accent" | "success" | "warning" | "danger";

const toneClasses: Record<StatusTone, string> = {
  neutral: "bg-muted-background text-muted",
  accent: "bg-accent/10 text-accent",
  success: "bg-success-background text-success",
  warning: "bg-warning-background text-warning",
  danger: "bg-danger-background text-danger",
};

type StatusPillProps = {
  label: string;
  tone?: StatusTone;
  className?: string;
};

export function StatusPill({ label, tone = "neutral", className }: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        toneClasses[tone],
        className,
      )}
    >
      {label}
    </span>
  );
}
