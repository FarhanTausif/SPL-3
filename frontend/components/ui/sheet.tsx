"use client";
import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
export const Sheet = Dialog.Root;
export const SheetTrigger = Dialog.Trigger;
export const SheetTitle = Dialog.Title;
export const SheetDescription = Dialog.Description;
export const SheetContent = React.forwardRef<
  React.ElementRef<typeof Dialog.Content>,
  React.ComponentPropsWithoutRef<typeof Dialog.Content>
>(({ children, className, ...props }, ref) => (
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
    <Dialog.Content
      ref={ref}
      className={cn(
        "fixed inset-y-0 left-0 z-50 w-80 max-w-[85vw] overflow-auto border-r bg-card p-4 shadow-xl",
        className
      )}
      {...props}
    >
      {children}
      <Dialog.Close
        className="absolute right-3 top-3 rounded-md p-2 text-muted-foreground hover:bg-muted"
        aria-label="Close history"
      >
        <X className="size-4" />
      </Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
));
SheetContent.displayName = "SheetContent";
