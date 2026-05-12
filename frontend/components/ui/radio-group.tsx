import * as React from 'react'
import { cn } from '@/lib/utils'

function RadioGroup({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div role="radiogroup" className={cn('grid gap-2', className)} {...props} />
}

const RadioGroupItem = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    type="radio"
    className={cn('h-4 w-4 accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring', className)}
    {...props}
  />
))
RadioGroupItem.displayName = 'RadioGroupItem'

export { RadioGroup, RadioGroupItem }
