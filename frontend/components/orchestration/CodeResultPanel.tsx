'use client'

import { useMemo, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { RunDetail, RunResponse } from '@/lib/api'

export function CodeResultPanel({ runResponse }: { runResponse?: RunResponse | RunDetail | null }) {
  const [copied, setCopied] = useState(false)
  const code = runResponse?.coder_output?.code
  const repair = runResponse?.repair_result?.attempts?.[runResponse.repair_result.attempts.length - 1]
  const finalCode = repair?.output_code || code
  const title = repair?.output_code ? 'Repaired Code' : 'Generated Code'

  const metadata = useMemo(() => {
    if (!runResponse?.coder_output) return []
    return [
      ['Language', runResponse.coder_output.language],
      ['Generator', `${runResponse.coder_output.provider} ${runResponse.coder_output.model}`.trim()],
      ['Dependencies', runResponse.coder_output.dependencies.join(', ') || 'None reported'],
    ]
  }, [runResponse])

  const handleCopy = () => {
    if (!finalCode) return
    navigator.clipboard.writeText(finalCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>Final code returned after verification and mitigation.</CardDescription>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={handleCopy} disabled={!finalCode}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {metadata.length > 0 && (
          <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
            {metadata.map(([label, value]) => (
              <div key={label} className="rounded-md border bg-muted/30 p-3">
                <p className="text-xs uppercase text-muted-foreground">{label}</p>
                <p className="mt-1 truncate font-medium">{value}</p>
              </div>
            ))}
          </div>
        )}
        <ScrollArea className="max-h-96 rounded-md border bg-slate-950 p-4 text-slate-50">
          <pre className="whitespace-pre-wrap break-words text-sm leading-6">
            {finalCode || 'Code will appear after the generation stage completes.'}
          </pre>
        </ScrollArea>
        {repair?.input_code && repair.output_code && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs uppercase text-muted-foreground">Before mitigation</p>
              <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-md border bg-muted p-3 text-xs">
                {repair.input_code}
              </pre>
            </div>
            <div>
              <p className="mb-2 text-xs uppercase text-muted-foreground">After mitigation</p>
              <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-md border bg-muted p-3 text-xs">
                {repair.output_code}
              </pre>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
