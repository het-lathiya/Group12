import axe from "axe-core";

/**
 * Rules that need a real layout. jsdom has none, so the unit helper turns them off; the Playwright
 * helper (e2e/axe.ts) runs the same axe-core rule set in a browser with them on.
 */
export const LAYOUT_RULES = ["color-contrast"] as const;

/** The axe rule IDs an element violates. jsdom has no layout, so colour contrast cannot run here. */
export async function axeViolations(element: Element): Promise<string[]> {
  const { violations } = await axe.run(element, {
    rules: Object.fromEntries(
      LAYOUT_RULES.map((rule) => [rule, { enabled: false }]),
    ),
  });
  return violations.map((violation) => violation.id);
}
