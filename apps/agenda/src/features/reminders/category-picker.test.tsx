import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CategoryPicker } from "./category-picker";

describe("CategoryPicker", () => {
  it("marks the default category as selected", () => {
    render(<CategoryPicker name="reminder_type" defaultValue="car" />);

    expect(screen.getByRole("button", { name: "Car" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(document.querySelector('input[name="reminder_type"]')).toHaveValue("car");
  });

  it("updates the hidden input when a different category is clicked", async () => {
    const user = userEvent.setup();
    render(<CategoryPicker name="reminder_type" defaultValue="car" />);

    await user.click(screen.getByRole("button", { name: "House" }));

    expect(screen.getByRole("button", { name: "House" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Car" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(document.querySelector('input[name="reminder_type"]')).toHaveValue("house");
  });
});
