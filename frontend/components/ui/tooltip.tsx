import * as React from 'react'
import { cn } from '@/lib/utils'

function Tooltip({ children }: { children: React.ReactNode }) {
  return <span className="group relative inline-flex">{children}</span>
}

function TooltipTrigger({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}

function TooltipContent({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        'pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 hidden -translate-x-1/2 rounded-md border bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md group-hover:block group-focus-within:block',
        className
      )}
      {...props}
    />
  )
}

export { Tooltip, TooltipTrigger, TooltipContent }
