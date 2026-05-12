import * as React from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

function Accordion({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('divide-y divide-border', className)} {...props} />
}

function AccordionItem({ className, ...props }: React.HTMLAttributes<HTMLDetailsElement>) {
  return <details className={cn('group', className)} {...props} />
}

function AccordionTrigger({ className, children, ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <summary
      className={cn(
        'flex cursor-pointer list-none items-center justify-between py-3 text-sm font-medium transition-colors hover:text-primary',
        className
      )}
      {...props}
    >
      {children}
      <ChevronDown className="h-4 w-4 shrink-0 transition-transform group-open:rotate-180" />
    </summary>
  )
}

function AccordionContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('pb-3 text-sm text-muted-foreground', className)} {...props} />
}

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
