"use client";

import { useCallback } from "react";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { GymDetailPanel } from "@/components/gyms/GymDetailPanel";

interface GymDetailModalProps {
  open: boolean;
  onOpenChange?: (open: boolean) => void;
  slug: string | null;
  onRequestClose?: () => void;
}

export function GymDetailModal({ open, onOpenChange, slug, onRequestClose }: GymDetailModalProps) {
  const handleClose = useCallback(() => {
    onOpenChange?.(false);
    onRequestClose?.();
  }, [onOpenChange, onRequestClose]);

  const handleOpenChange = useCallback(
    (next: boolean) => {
      onOpenChange?.(next);
      if (!next) {
        onRequestClose?.();
      }
    },
    [onOpenChange, onRequestClose],
  );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[88vh] w-full max-w-3xl overflow-hidden border-none bg-transparent p-0 shadow-none [&>button]:hidden">
        <div className="max-h-[88vh] overflow-y-auto rounded-2xl border border-border/70 bg-background shadow-2xl">
          <GymDetailPanel
            className="rounded-none border-none bg-transparent shadow-none"
            onClose={handleClose}
            slug={slug}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
