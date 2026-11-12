"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel: string;
  onConfirm: () => void;
  /** Destructive style for an action that removes something (ui-design.md). */
  destructive?: boolean;
};

/** A yes-or-no question before an action (§7.6 shared states): Cancel, then the action. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  onConfirm,
  destructive = false,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" className="min-h-touch">
              Cancel
            </Button>
          </DialogClose>
          <Button
            variant={destructive ? "destructive" : "default"}
            className="min-h-touch"
            onClick={() => {
              onOpenChange(false);
              onConfirm();
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
