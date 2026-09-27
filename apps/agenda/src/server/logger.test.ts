// @vitest-environment node
import { describe, expect, it } from "vitest";

import { errorFields } from "./logger";

describe("errorFields", () => {
  it("keeps the message and stack of an Error", () => {
    const fields = errorFields(new TypeError("bad input"));

    expect(fields.error).toBe("TypeError: bad input");
    expect(fields.exception).toContain("TypeError: bad input");
  });

  it("stringifies non-Error values", () => {
    expect(errorFields("nope")).toEqual({ error: "nope" });
  });
});
