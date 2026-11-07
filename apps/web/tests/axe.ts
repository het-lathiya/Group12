import axe from "axe-core";

/** The axe rule IDs an element violates. jsdom has no layout, so colour contrast cannot run here. */
export async function axeViolations(element: Element): Promise<string[]> {
  const { violations } = await axe.run(element, {
    rules: { "color-contrast": { enabled: false } },
  });
  return violations.map((violation) => violation.id);
}
