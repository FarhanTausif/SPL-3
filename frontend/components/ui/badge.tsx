import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex w-fit max-w-full items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-semibold capitalize leading-4 transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-stone-900 text-white",
        neutral: "border-stone-200 bg-stone-100 text-stone-600",
        good: "border-emerald-200 bg-emerald-50 text-emerald-800",
        warn: "border-amber-200 bg-amber-50 text-amber-800",
        bad: "border-red-200 bg-red-50 text-red-800",
        info: "border-sky-200 bg-sky-50 text-sky-800"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
