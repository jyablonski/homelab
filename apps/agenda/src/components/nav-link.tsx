"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type NavLinkProps = {
  href: string;
  children: ReactNode;
  count?: number | null;
};

export function NavLink({ href, children, count }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={cn(
        "flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors",
        isActive
          ? "bg-accent/15 text-foreground"
          : "text-muted hover:bg-muted-background hover:text-foreground",
      )}
    >
      <span className="flex items-center gap-2">
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            isActive ? "bg-accent" : "bg-transparent",
          )}
        />
        {children}
      </span>
      {count ? <span className="text-xs text-muted">{count}</span> : null}
    </Link>
  );
}
