import { SearchX } from "lucide-react";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border px-6 py-12 text-center">
      <SearchX className="h-8 w-8 text-muted" />
      <p className="text-sm font-medium text-foreground">Page not found</p>
      <Link href="/" className="text-sm text-accent hover:underline">
        Back to today
      </Link>
    </div>
  );
}
