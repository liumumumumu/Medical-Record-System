import { describe, expect, it } from "vitest";
import { utf8ByteLength } from "./login-dialog";

describe("utf8ByteLength", () => {
  it("counts ASCII and Chinese password bytes as UTF-8", () => {
    expect(utf8ByteLength("Password123")).toBe(11);
    expect(utf8ByteLength("密".repeat(24))).toBe(72);
    expect(utf8ByteLength("密".repeat(25))).toBe(75);
  });
});
