import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import NewReminderPage from "./page";

describe("NewReminderPage", () => {
  it("renders the reminder form in create mode", () => {
    render(<NewReminderPage />);
    expect(screen.getByRole("heading", { name: "New reminder" })).toBeInTheDocument();
  });
});
