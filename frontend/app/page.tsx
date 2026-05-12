'use client'

import { Activity, Cpu, Network, ShieldCheck, Users } from 'lucide-react'
import { VerificationForm } from '@/components/VerificationForm'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { useHealth } from '@/hooks/useRunStatus'

const flowPreview = [
  ['Prompt', 'Clarify'],
  ['Generate', 'Extract claims'],
  ['Static', 'Sandbox'],
  ['Judge', 'CoVE'],
  ['Panel', 'Policy'],
  ['Repair', 'Result'],
]

export default function Home() {
  const { data: health, error: healthError, isLoading: healthLoading } = useHealth()
  const providers = health ? Object.entries(health.providers) : []
  const workerReady = Boolean(health?.orchestration.worker_readiness?.ready)

  return (
    <main className="min-h-screen bg-background px-4 py-6 text-foreground">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="flex flex-col gap-4 rounded-lg border border-white/10 bg-card/80 p-5 shadow-2xl shadow-black/30 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="rounded-md border border-white/10 bg-black/30 p-2">
                <ShieldCheck className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-normal md:text-3xl">DeHalu Orchestration Console</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  Live CrewAI hallucination detection, verification, policy, and mitigation flow.
                </p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <HealthMetric icon={Activity} label="API" value={healthLoading ? 'checking' : health?.status || 'offline'} ready={health?.status === 'ok'} />
            <HealthMetric icon={Users} label="CrewAI" value={health?.orchestration.crewai_enabled ? 'enabled' : 'available'} ready={Boolean(health?.orchestration.crewai_available)} />
            <HealthMetric icon={Cpu} label="Worker" value={String(health?.orchestration.worker_readiness?.state || 'unknown')} ready={workerReady} />
            <HealthMetric icon={Network} label="Queue" value={String(health?.orchestration.queue_backlog?.total ?? 0)} ready={!health?.orchestration.queue_backlog?.has_backlog} />
          </div>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(460px,1.05fr)]">
          <VerificationForm />

          <div className="space-y-6">
            <Card className="border-white/10 bg-card/80 shadow-2xl shadow-black/20">
              <CardHeader>
                <CardTitle>Backend Flow Preview</CardTitle>
                <CardDescription>
                  The monitor renders this graph from run events and evidence once execution starts.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                  {flowPreview.flat().map((stage, index) => (
                    <div key={stage} className="rounded-lg border border-white/10 bg-black/30 p-4">
                      <p className="text-xs text-muted-foreground">Step {index + 1}</p>
                      <p className="mt-1 text-sm font-semibold">{stage}</p>
                    </div>
                  ))}
                </div>
                <Separator className="my-5" />
                <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                  <InfoRow label="Orchestration mode" value={healthLoading ? 'checking' : health?.orchestration.configured_mode || 'unavailable'} />
                  <InfoRow label="Routing policy" value={healthLoading ? 'checking' : health?.orchestration.routing_policy_version || 'unavailable'} />
                  <InfoRow label="Prompt policy" value={healthLoading ? 'checking' : health?.orchestration.prompt_policy_version || 'unavailable'} />
                  <InfoRow label="Strictness" value="very strict" />
                </div>
                {healthError && (
                  <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                    Backend health is not reachable from the browser. Confirm the API is running on port 8000.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-card/80 shadow-2xl shadow-black/20">
              <CardHeader>
                <CardTitle>Provider Readiness</CardTitle>
                <CardDescription>Model availability and routing health from the backend.</CardDescription>
              </CardHeader>
              <CardContent>
                {providers.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Provider readiness is loading.</p>
                ) : (
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    {providers.map(([name, ready]) => {
                      const details = health?.orchestration.provider_health_details?.[name]
                      return (
                        <div key={name} className="rounded-lg border border-white/10 bg-black/30 p-4">
                          <div className="flex items-center justify-between gap-3">
                            <p className="font-medium">{name}</p>
                            <Badge variant={ready ? 'success' : 'warning'}>{ready ? 'ready' : 'degraded'}</Badge>
                          </div>
                          <p className="mt-2 text-xs text-muted-foreground">
                            Smoke: {String(details?.live_smoke_check || 'unknown')} · API key: {details?.api_key_present ? 'present' : 'not present'}
                          </p>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  )
}

function HealthMetric({
  icon: Icon,
  label,
  value,
  ready,
}: {
  icon: typeof Activity
  label: string
  value: string
  ready: boolean
}) {
  return (
    <div className="rounded-md border border-white/10 bg-black/30 p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="mt-1 flex items-center gap-2">
        <span className="truncate text-sm font-semibold">{value}</span>
        <span className={`h-2 w-2 rounded-full ${ready ? 'bg-emerald-500' : 'bg-amber-500'}`} />
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-white/10 bg-black/30 px-3 py-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="truncate font-medium">{value}</span>
    </div>
  )
}
