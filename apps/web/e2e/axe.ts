import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { LAYOUT_RULES } from "../tests/axe";

/**
 * NFR-025: run axe on the page as it is now. Critical violations fail the test; serious ones are
 * listed in the output and as a test annotation. Same axe-core rules as tests/axe.ts, with the
 * layout rules on, because a browser has a layout.
 */
export async function checkA11y(page: Page): Promise<void> {
  const { violations } = await new AxeBuilder({ page })
    .options({
      rules: Object.fromEntries(
        LAYOUT_RULES.map((rule) => [rule, { enabled: true }]),
      ),
    })
    .analyze();
  const describe = (impact: string) =>
    violations
      .filter((violation) => violation.impact === impact)
      .map(
        (violation) =>
          `${violation.id} (${violation.nodes.length}): ${violation.help}`,
      );

  const serious = describe("serious");
  if (serious.length > 0) {
    const where = new URL(page.url()).pathname;
    console.log(`axe serious on ${where}:\n  ${serious.join("\n  ")}`);
    test.info().annotations.push({
      type: "axe-serious",
      description: `${where}: ${serious.join("; ")}`,
    });
  }
  expect(describe("critical"), "critical axe violations (NFR-025)").toEqual([]);
}
