import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex w-fit max-w-full items-center rounded-sm border px-1.5 py-0.5 text-xs font-semibold capitalize leading-4 transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-stone-900 text-white",
        neutral: "border-border bg-muted text-muted-foreground",
        good: "border-emerald-200 bg-good-surface text-good",
        warn: "border-amber-200 bg-warning-surface text-warning",
        bad: "border-red-200 bg-danger-surface text-danger",
        info: "border-sky-200 bg-active-surface text-active"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
