import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NewReminderLink } from "./new-reminder-link";

describe("NewReminderLink", () => {
  it("links to the new reminder page", () => {
    render(<NewReminderLink />);
    expect(screen.getByRole("link", { name: /New reminder/ })).toHaveAttribute(
      "href",
      "/reminders/new",
    );
  });
});
