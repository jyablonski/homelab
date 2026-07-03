import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgendaSection } from "./agenda-section";

describe("AgendaSection", () => {
  it("renders the title, count, and children", () => {
    render(
      <AgendaSection title="Due soon" count={3}>
        <p>Pay electric bill</p>
      </AgendaSection>,
    );

    expect(screen.getByText("Due soon")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Pay electric bill")).toBeInTheDocument();
  });
});
