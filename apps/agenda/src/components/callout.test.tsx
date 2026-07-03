import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Callout } from "./callout";

describe("Callout", () => {
  it("renders its children", () => {
    render(<Callout>Helpful guidance</Callout>);
    expect(screen.getByText("Helpful guidance")).toBeInTheDocument();
  });
});
