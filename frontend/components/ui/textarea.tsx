import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      className={cn(
        "flex min-h-[96px] w-full resize-none rounded-md border border-stone-200 bg-white px-3 py-2 text-sm leading-6 text-stone-950 placeholder:text-stone-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700/25 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      ref={ref}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";

export { Textarea };
