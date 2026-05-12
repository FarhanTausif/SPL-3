'use client'

import { EventRecord, EvidenceRecord } from '@/lib/api'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function EvidenceTimeline({
  evidence,
  events,
}: {
  evidence: EvidenceRecord[]
  events: EventRecord[]
}) {
  return (
    <Tabs defaultValue="evidence">
      <TabsList>
        <TabsTrigger value="evidence">Evidence</TabsTrigger>
        <TabsTrigger value="events">Events</TabsTrigger>
      </TabsList>
      <TabsContent value="evidence">
        <ScrollArea className="max-h-80 rounded-lg border bg-card p-4">
          {evidence.length === 0 ? (
            <p className="text-sm text-muted-foreground">Evidence will appear as the backend records verification outputs.</p>
          ) : (
            <Accordion className="space-y-2">
              {evidence.map((item, index) => (
                <AccordionItem key={item.id || `${item.kind}-${index}`} className="rounded-md border px-3">
                  <AccordionTrigger>
                    <span className="flex min-w-0 items-center gap-2">
                      <Badge variant="outline">{item.kind}</Badge>
                      <span className="truncate text-left text-sm">
                        {String(item.payload.task_name || item.payload.stage || item.kind)}
                      </span>
                    </span>
                  </AccordionTrigger>
                  <AccordionContent>
                    <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted p-3 text-xs">
                      {JSON.stringify(item.payload, null, 2)}
                    </pre>
                    {item.created_at && (
                      <p className="mt-2 text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p>
                    )}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </ScrollArea>
      </TabsContent>
      <TabsContent value="events">
        <ScrollArea className="max-h-80 rounded-lg border bg-card p-4">
          {events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No run events received yet.</p>
          ) : (
            <div className="space-y-3">
              {events.map((event) => (
                <div key={event.sequence} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-2">
                      <Badge variant="muted">#{event.sequence}</Badge>
                      <p className="truncate text-sm font-medium">{event.event_type}</p>
                    </div>
                    <Badge variant="outline">{event.status}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{event.message}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {event.stage}{event.created_at ? ` · ${new Date(event.created_at).toLocaleString()}` : ''}
                  </p>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </TabsContent>
    </Tabs>
  )
}
