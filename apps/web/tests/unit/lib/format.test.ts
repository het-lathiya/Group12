import { describe, expect, it } from "vitest";

import { formatDayDate, formatFullDate } from "@/lib/format";

describe("date formatting", () => {
  it("IMD-135: source retrieval dates show the year", () => {
    expect(formatFullDate("2026-10-31")).toBe("31 Oct 2026");
    expect(formatFullDate("2027-01-01")).toBe("1 Jan 2027");
  });

  it("day labels keep the short form without the year", () => {
    expect(formatDayDate("2026-11-14")).toBe("Sat 14 Nov");
  });
});
