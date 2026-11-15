import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { VersionList } from "@/components/versions/VersionList";
import type { components } from "@/lib/api/schema";

type Version = components["schemas"]["VersionOut"];

const version = (overrides: Partial<Version>): Version => ({
  id: "00000000-0000-4000-8000-000000000010",
  version_no: 1,
  name: null,
  reason: "generation",
  kind: "automatic",
  plan_revision: 1,
  validation_summary: { errors: 0, warnings: 2, infos: 1 },
  generation_id: null,
  created_at: "2026-11-15T10:00:00Z",
  ...overrides,
});

const VERSIONS = [
  version({
    id: "v3",
    version_no: 3,
    name: "Before the museum day",
    reason: "manual",
    kind: "named",
    plan_revision: 2,
  }),
  version({ id: "v2", version_no: 2, reason: "edit", plan_revision: 2 }),
  version({ id: "v1", version_no: 1 }),
];

it("lists every version from the API with its kind, reason and finding counts", () => {
  render(
    <VersionList versions={VERSIONS} currentRevision={2} onRestore={vi.fn()} />,
  );
  const rows = within(
    screen.getByRole("list", { name: "Saved versions" }),
  ).getAllByRole("listitem");
  expect(rows).toHaveLength(3);
  expect(rows[0]).toHaveTextContent("Version 3: Before the museum day");
  expect(rows[0]).toHaveTextContent("Named");
  expect(rows[1]).toHaveTextContent("Version 2: After an edit");
  expect(rows[2]).toHaveTextContent("Version 1: Generated plan");
  expect(rows[2]).toHaveTextContent("Automatic");
  expect(rows[2]).toHaveTextContent("0 errors, 2 warnings, 1 notes");
  // The plan in use is marked and cannot be restored.
  expect(rows[0]).toHaveTextContent("Current plan");
  expect(
    within(rows[0]).queryByRole("button", { name: /Restore/ }),
  ).not.toBeInTheDocument();
});

it("restores only after the confirmation", () => {
  const onRestore = vi.fn();
  render(
    <VersionList
      versions={VERSIONS}
      currentRevision={2}
      onRestore={onRestore}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Restore version 1" }));
  const dialog = screen.getByRole("dialog", { name: "Restore version 1?" });
  expect(onRestore).not.toHaveBeenCalled();
  fireEvent.click(within(dialog).getByRole("button", { name: "Restore" }));
  expect(onRestore).toHaveBeenCalledWith(VERSIONS[2]);
});

it("cancel closes the confirmation without restoring", () => {
  const onRestore = vi.fn();
  render(
    <VersionList
      versions={VERSIONS}
      currentRevision={2}
      onRestore={onRestore}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Restore version 1" }));
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(onRestore).not.toHaveBeenCalled();
});

it("disables Restore while a restore is saving", () => {
  render(
    <VersionList
      versions={VERSIONS}
      currentRevision={2}
      onRestore={vi.fn()}
      restoring
    />,
  );
  expect(
    screen.getByRole("button", { name: "Restore version 1" }),
  ).toBeDisabled();
});
