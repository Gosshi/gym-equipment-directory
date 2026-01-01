import type * as React from "react";
import * as ToastPrimitives from "@radix-ui/react-toast";
import { cva, type VariantProps } from "class-variance-authority";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

const toastVariants = cva(
  "group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border border-border bg-background p-4 pr-6 text-sm shadow-lg transition-all",
  {
    variants: {
      variant: {
        default: "border bg-background text-foreground",
        destructive: "destructive group text-destructive-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export const ToastProvider = ToastPrimitives.Provider;

export function ToastViewport({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Viewport> & {
  ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Viewport>>;
}) {
  return (
    <ToastPrimitives.Viewport
      ref={ref}
      className={cn(
        "fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse gap-2 p-4 sm:flex-col sm:p-6",
        className,
      )}
      {...props}
    />
  );
}

ToastViewport.displayName = ToastPrimitives.Viewport.displayName;

export function Toast({
  className,
  variant,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Root> &
  VariantProps<typeof toastVariants> & {
    ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Root>>;
  }) {
  return (
    <ToastPrimitives.Root
      ref={ref}
      className={cn(toastVariants({ variant }), className)}
      {...props}
    />
  );
}

Toast.displayName = ToastPrimitives.Root.displayName;

export function ToastAction({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Action> & {
  ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Action>>;
}) {
  return (
    <ToastPrimitives.Action
      ref={ref}
      className={cn(
        "inline-flex h-8 shrink-0 items-center justify-center rounded-md border border-input bg-transparent px-3 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

ToastAction.displayName = ToastPrimitives.Action.displayName;

export function ToastClose({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Close> & {
  ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Close>>;
}) {
  return (
    <ToastPrimitives.Close
      ref={ref}
      className={cn(
        "absolute right-1 top-1 rounded-md p-1 text-foreground/50 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 focus:outline-none focus:ring-1 focus:ring-ring group-hover:opacity-100",
        className,
      )}
      toast-close=""
      {...props}
    >
      <X className="h-4 w-4" />
    </ToastPrimitives.Close>
  );
}

ToastClose.displayName = ToastPrimitives.Close.displayName;

export function ToastTitle({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Title> & {
  ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Title>>;
}) {
  return (
    <ToastPrimitives.Title
      ref={ref}
      className={cn("text-sm font-semibold", className)}
      {...props}
    />
  );
}

ToastTitle.displayName = ToastPrimitives.Title.displayName;

export function ToastDescription({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Description> & {
  ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Description>>;
}) {
  return (
    <ToastPrimitives.Description
      ref={ref}
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  );
}

ToastDescription.displayName = ToastPrimitives.Description.displayName;

export type ToastProps = React.ComponentPropsWithoutRef<typeof Toast>;
export type ToastActionElement = React.ReactElement<typeof ToastAction>;
