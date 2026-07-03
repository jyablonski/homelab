import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Field } from "./field";

describe("Field", () => {
  it("renders the label and children", () => {
    render(
      <Field label="Message" htmlFor="message">
        <textarea id="message" />
      </Field>,
    );

    expect(screen.getByText("Message")).toBeInTheDocument();
    expect(screen.getByLabelText("Message")).toBeInTheDocument();
  });

  it("shows a hint when there is no error", () => {
    render(
      <Field label="End date" htmlFor="end" hint="Optional">
        <input id="end" />
      </Field>,
    );

    expect(screen.getByText("Optional")).toBeInTheDocument();
  });

  it("shows an error instead of the hint", () => {
    render(
      <Field label="Message" htmlFor="message" hint="Optional" error="Required">
        <textarea id="message" />
      </Field>,
    );

    expect(screen.getByText("Required")).toBeInTheDocument();
    expect(screen.queryByText("Optional")).not.toBeInTheDocument();
  });
});
