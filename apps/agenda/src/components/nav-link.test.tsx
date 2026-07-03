import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const usePathnameMock = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ usePathname: usePathnameMock }));

import { NavLink } from "./nav-link";

describe("NavLink", () => {
  it("marks the Today link active only on the root path", () => {
    usePathnameMock.mockReturnValue("/");
    render(<NavLink href="/">Today</NavLink>);
    expect(screen.getByRole("link", { name: "Today" })).toHaveClass("bg-accent/15");
  });

  it("marks a nested route active by prefix", () => {
    usePathnameMock.mockReturnValue("/reminders/1/edit");
    render(<NavLink href="/reminders/1/edit">Edit</NavLink>);
    expect(screen.getByRole("link", { name: "Edit" })).toHaveClass("bg-accent/15");
  });

  it("does not mark an unrelated route active", () => {
    usePathnameMock.mockReturnValue("/completed");
    render(<NavLink href="/upcoming">Upcoming</NavLink>);
    expect(screen.getByRole("link", { name: "Upcoming" })).not.toHaveClass(
      "bg-accent/15",
    );
  });

  it("renders a count badge when provided", () => {
    usePathnameMock.mockReturnValue("/completed");
    render(
      <NavLink href="/completed" count={24}>
        Completed
      </NavLink>,
    );
    expect(screen.getByText("24")).toBeInTheDocument();
  });

  it("omits the badge when count is zero or missing", () => {
    usePathnameMock.mockReturnValue("/completed");
    render(
      <NavLink href="/completed" count={0}>
        Completed
      </NavLink>,
    );
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });
});
