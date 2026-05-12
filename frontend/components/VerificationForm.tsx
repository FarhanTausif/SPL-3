'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { AlertCircle, Loader2, Play } from 'lucide-react'
import { runApi, CreateRunRequest } from '@/lib/api'
import { useRunStore } from '@/stores/runStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'

export function VerificationForm() {
  const router = useRouter()
  const setRunId = useRunStore((state) => state.setRunId)

  const [prompt, setPrompt] = useState('')
  const [validationError, setValidationError] = useState('')

  useEffect(() => {
    const savedPrompt = window.localStorage.getItem('dehalu.promptDraft')
    if (savedPrompt) setPrompt(savedPrompt)
  }, [])

  const updatePrompt = (value: string) => {
    setPrompt(value)
    window.localStorage.setItem('dehalu.promptDraft', value)
  }

  const mutation = useMutation({
    mutationFn: (request: CreateRunRequest) => runApi.createRun(request),
    onSuccess: (response) => {
      setRunId(response.run_id)
      router.push(`/monitor/${response.run_id}`)
    },
    onError: (error: Error) => {
      setValidationError(error.message)
    },
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    setValidationError('')

    if (!prompt.trim()) {
      setValidationError('Prompt is required.')
      return
    }
    if (prompt.trim().length < 10) {
      setValidationError('Prompt must be at least 10 characters.')
      return
    }
    if (prompt.trim().length > 5000) {
      setValidationError('Prompt must not exceed 5000 characters.')
      return
    }

    mutation.mutate({
      prompt: prompt.trim(),
      risk_level: 'high',
      run_mode: 'advanced',
      latency_budget_seconds: 90,
      acceptance_criteria: [],
      tool_policy: {
        max_calls_per_role: 5,
        timeout_seconds: 12,
        allow_repo_context: true,
        allow_web_lookup: true,
        allowed_domains: ['pypi.org'],
      },
    })
  }

  return (
    <Card className="border-white/10 bg-card/90 shadow-2xl shadow-black/30">
      <CardHeader>
        <CardTitle>Prompt Workspace</CardTitle>
        <CardDescription>
          The code model generates the code; the crew verifies, detects hallucinations, and applies mitigation.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="prompt" className="text-sm font-medium">Generation prompt</label>
            <Textarea
              id="prompt"
              value={prompt}
              onChange={(event) => updatePrompt(event.target.value)}
              placeholder="Write a function for fibonacci series"
              rows={12}
              className="mt-2 resize-none border-white/10 bg-black/30 text-base leading-7 shadow-inner shadow-black/30 placeholder:text-muted-foreground/70"
            />
            <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
              <span>Language, framework, runtime, and checks are inferred by the agentic pipeline.</span>
              <span>{prompt.length}/5000</span>
            </div>
          </div>

          {validationError && (
            <div className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{validationError}</span>
            </div>
          )}

          <Button type="submit" disabled={mutation.isPending} className="h-11 w-full bg-blue-500 text-base font-semibold text-white shadow-lg shadow-blue-950/40 hover:bg-blue-400">
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {mutation.isPending ? 'Creating run...' : 'Start orchestration'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
