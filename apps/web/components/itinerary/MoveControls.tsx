"use client";

import {
  closestCorners,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useIsMutating } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, GripVertical } from "lucide-react";
import {
  createContext,
  type ReactNode,
  useContext,
  useId,
  useState,
} from "react";
import { toast } from "sonner";

import { CONTROL_CLASS } from "@/components/trips/Field";
import { Button } from "@/components/ui/button";
import { describeError } from "@/lib/api/errors";
import { editKey, useMoveItem } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { cn } from "@/lib/utils";

type Item = components["schemas"]["Item"];
type Action = "up" | "down" | "day" | "drag";

const ANNOUNCER_ID = "move-announcer";

/** Where a dragged item was and where it was dropped: an item (its slot) or a day (its end). */
export type DragSpot = { item?: Item; dayNumber: number; position?: number };

/**
 * The API-26 body for a drop (TC-197), or null when nothing moves. Dropped on an item, the dragged
 * item takes that item's position; dropped on another day, it goes after that day's last item.
 */
export function dropMove(
  from: DragSpot,
  to: DragSpot,
): { day_number: number; position?: number } | null {
  if (to.position === undefined)
    return to.dayNumber === from.dayNumber
      ? null
      : { day_number: to.dayNumber };
  if (to.dayNumber === from.dayNumber && to.position === from.position)
    return null;
  return { day_number: to.dayNumber, position: to.position };
}

/** One move through API-26; after the answer, announce it and keep focus on the item's controls. */
function useMove(tripId: string, planRevision: number) {
  const mutation = useMoveItem(tripId);
  return (
    item: Item,
    target: { day_number?: number; position?: number },
    action: Action,
  ) =>
    mutation.mutate(
      { itemId: item.id, plan_revision: planRevision, ...target },
      {
        onSuccess: (result) => {
          const day = result.changed_days.find((d) =>
            d.items.some(({ id }) => id === item.id),
          );
          const moved = day?.items.find(({ id }) => id === item.id);
          const region = document.getElementById(ANNOUNCER_ID);
          if (day && moved && region)
            region.textContent = `Moved ${item.place.name} to day ${day.day_number} position ${moved.position}`;
          requestAnimationFrame(() =>
            focusControls(item.id, action, day?.day_number),
          );
        },
        onError: (error) => {
          const { what, next } = describeError(error);
          toast.error(what, { description: next });
        },
      },
    );
}

// One move function per plan, owned by MoveDndContext: it stays mounted when a move to another day
// unmounts the item's own controls, so the answer is still announced and focus still moves.
type Move = ReturnType<typeof useMove>;
const MoveContext = createContext<Move | null>(null);

function focusControls(itemId: string, action: Action, dayNumber?: number) {
  const group = document.querySelector(`[data-move-for="${itemId}"]`);
  if (!group) {
    // Below 768 px the item's new day is a closed tab: focusing that tab opens it (automatic
    // activation), so focus is never lost to the page body.
    const tab = [
      ...document.querySelectorAll<HTMLElement>('[role="tab"]'),
    ].find((t) => t.textContent?.trim() === `Day ${dayNumber}`);
    tab?.focus();
    return;
  }
  const buttons = [...group.querySelectorAll<HTMLButtonElement>("button")];
  const same = buttons.find((b) => b.dataset.action === action && !b.disabled);
  (same ?? buttons.find((b) => !b.disabled))?.focus();
}

/**
 * The drag area of the whole plan (pointer and keyboard sensors) and the polite live region that
 * announces each move. A drop calls API-26; nothing is reordered until the server answers.
 */
export function MoveDndContext({
  tripId,
  planRevision,
  children,
}: {
  tripId: string;
  planRevision: number;
  children: ReactNode;
}) {
  const move = useMove(tripId, planRevision);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  function onDragEnd({ active, over }: DragEndEvent) {
    const from = active.data.current as DragSpot | undefined;
    const to = over?.data.current as DragSpot | undefined;
    const target = from?.item && to ? dropMove(from, to) : null;
    if (from?.item && target) move(from.item, target, "drag");
  }

  return (
    <DndContext
      id={useId()}
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragEnd={onDragEnd}
    >
      <MoveContext.Provider value={move}>{children}</MoveContext.Provider>
      <p
        id={ANNOUNCER_ID}
        role="status"
        aria-live="polite"
        className="sr-only"
      />
    </DndContext>
  );
}

/** A day's list as a drop area: its items in order, and the day itself for "move to the end". */
export function SortableDay({
  dayNumber,
  itemIds,
  children,
}: {
  dayNumber: number;
  itemIds: string[];
  children: ReactNode;
}) {
  const { setNodeRef } = useDroppable({
    id: `day-${dayNumber}-drop`,
    data: { dayNumber } satisfies DragSpot,
  });
  return (
    <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
      <ol ref={setNodeRef} className="mt-4 min-h-touch">
        {children}
      </ol>
    </SortableContext>
  );
}

// The item's drag grip, built where useSortable runs and shown inside MoveControls.
const GripContext = createContext<ReactNode>(null);

/** One draggable list item; its grip button (shown in MoveControls) starts the drag. */
export function SortableItem({
  item,
  dayNumber,
  children,
}: {
  item: Item;
  dayNumber: number;
  children: ReactNode;
}) {
  const {
    attributes,
    listeners,
    setActivatorNodeRef,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: item.id,
    data: { item, dayNumber, position: item.position } satisfies DragSpot,
  });
  const busy = useIsMutating({ mutationKey: ["edit"] }) > 0;
  const grip = (
    <Button
      ref={setActivatorNodeRef}
      variant="ghost"
      size="icon"
      data-action="drag"
      disabled={busy}
      className="cursor-grab touch-none active:cursor-grabbing"
      {...attributes}
      {...listeners}
      aria-label={`Drag ${item.place.name} to reorder`}
    >
      <GripVertical aria-hidden="true" />
    </Button>
  );
  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={cn(isDragging && "relative z-10 opacity-80")}
    >
      <GripContext.Provider value={grip}>{children}</GripContext.Provider>
    </li>
  );
}

export type MoveControlsProps = {
  tripId: string;
  planRevision: number;
  item: Item;
  dayNumber: number;
  /** The number of items on the item's day, for the "Move down" edge. */
  itemCount: number;
  dayNumbers: number[];
};

/**
 * MoveControls (§7; FR-060, IMP-409): a drag grip plus Move up, Move down and Move (to the chosen day), the
 * keyboard and single-pointer equivalent of every drag (WCAG 2.2). Each calls API-26; the server's
 * answer replaces the plan, and any new conflict shows in WarningsPanel.
 */
export function MoveControls({
  tripId,
  planRevision,
  item,
  dayNumber,
  itemCount,
  dayNumbers,
}: MoveControlsProps) {
  const ownMove = useMove(tripId, planRevision);
  const move = useContext(MoveContext) ?? ownMove;
  const busy = useIsMutating({ mutationKey: editKey(tripId) }) > 0;
  const grip = useContext(GripContext);
  const otherDays = dayNumbers.filter((n) => n !== dayNumber);
  const [day, setDay] = useState(String(otherDays[0] ?? ""));
  const name = item.place.name;
  const selectId = `move-day-${item.id}`;

  return (
    <div
      role="group"
      aria-label={`Move ${name}`}
      data-move-for={item.id}
      className="mt-3 flex flex-wrap items-center gap-2"
    >
      {grip}
      <Button
        variant="outline"
        size="sm"
        className="min-h-touch"
        data-action="up"
        disabled={busy || item.position <= 1}
        aria-label={`Move ${name} up`}
        onClick={() =>
          move(
            item,
            { day_number: dayNumber, position: item.position - 1 },
            "up",
          )
        }
      >
        <ArrowUp aria-hidden="true" />
        Up
      </Button>
      <Button
        variant="outline"
        size="sm"
        className="min-h-touch"
        data-action="down"
        disabled={busy || item.position >= itemCount}
        aria-label={`Move ${name} down`}
        onClick={() =>
          move(
            item,
            { day_number: dayNumber, position: item.position + 1 },
            "down",
          )
        }
      >
        <ArrowDown aria-hidden="true" />
        Down
      </Button>
      {otherDays.length > 0 && (
        <span className="flex items-center gap-2">
          <label htmlFor={selectId} className="sr-only">
            Day to move {name} to
          </label>
          <select
            id={selectId}
            value={day}
            disabled={busy}
            onChange={(event) => setDay(event.target.value)}
            className={cn(CONTROL_CLASS, "w-auto")}
          >
            {otherDays.map((n) => (
              <option key={n} value={n}>
                Day {n}
              </option>
            ))}
          </select>
          <Button
            variant="outline"
            size="sm"
            className="min-h-touch"
            data-action="day"
            disabled={busy || day === ""}
            aria-label={`Move ${name} to day ${day}`}
            onClick={() => move(item, { day_number: Number(day) }, "day")}
          >
            {/* Visible text inside the accessible name (axe label-content-name-mismatch). */}
            Move
          </Button>
        </span>
      )}
    </div>
  );
}
