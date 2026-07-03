import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageHeader } from "./page-header";

describe("PageHeader", () => {
  it("renders the title only when subtitle and action are omitted", () => {
    render(<PageHeader title="Completed" />);
    expect(screen.getByRole("heading", { name: "Completed" })).toBeInTheDocument();
  });

  it("renders a subtitle and action when provided", () => {
    render(
      <PageHeader
        title="Today"
        subtitle="3 active · 2 due soon"
        action={<button>New reminder</button>}
      />,
    );

    expect(screen.getByText("3 active · 2 due soon")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New reminder" })).toBeInTheDocument();
  });
});
