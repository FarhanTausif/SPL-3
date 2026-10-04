"use client";
import * as React from "react";
import * as Primitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
export const Select = Primitive.Root;
export const SelectValue = Primitive.Value;
export const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof Primitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof Primitive.Trigger>
>(({ children, className, ...props }, ref) => (
  <Primitive.Trigger
    ref={ref}
    className={cn(
      "flex h-10 min-w-0 items-center justify-between gap-2 rounded-md border border-input bg-card px-3 text-sm [&>span]:truncate",
      className
    )}
    {...props}
  >
    {children}
    <Primitive.Icon asChild>
      <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
    </Primitive.Icon>
  </Primitive.Trigger>
));
SelectTrigger.displayName = "SelectTrigger";
export const SelectContent = React.forwardRef<
  React.ElementRef<typeof Primitive.Content>,
  React.ComponentPropsWithoutRef<typeof Primitive.Content>
>(({ children, ...props }, ref) => (
  <Primitive.Portal>
    <Primitive.Content
      ref={ref}
      position="popper"
      sideOffset={4}
      className="z-50 max-h-80 min-w-[var(--radix-select-trigger-width)] overflow-y-auto rounded-md border bg-popover p-1 shadow-md"
      {...props}
    >
      <Primitive.Viewport>{children}</Primitive.Viewport>
    </Primitive.Content>
  </Primitive.Portal>
));
SelectContent.displayName = "SelectContent";
export const SelectItem = React.forwardRef<
  React.ElementRef<typeof Primitive.Item>,
  React.ComponentPropsWithoutRef<typeof Primitive.Item>
>(({ children, ...props }, ref) => (
  <Primitive.Item
    ref={ref}
    className="relative cursor-pointer rounded-sm py-2 pl-8 pr-3 text-sm outline-none focus:bg-muted data-[disabled]:opacity-50"
    {...props}
  >
    <Primitive.ItemIndicator className="absolute left-2">
      <Check className="size-4" />
    </Primitive.ItemIndicator>
    <Primitive.ItemText>{children}</Primitive.ItemText>
  </Primitive.Item>
));
SelectItem.displayName = "SelectItem";
