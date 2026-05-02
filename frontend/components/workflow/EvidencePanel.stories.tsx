import type { Meta, StoryObj } from '@storybook/react'
import { EvidencePanel } from '@/components/workflow/EvidencePanel'

const meta = {
  title: 'Workflow/EvidencePanel',
  component: EvidencePanel,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'Displays collected evidence from verification stages with expandable details.',
      },
    },
  },
  tags: ['autodocs'],
} satisfies Meta<typeof EvidencePanel>

export default meta
type Story = StoryObj<typeof meta>

const sampleEvidence = [
  {
    kind: 'claim_extraction' as const,
    summary: '9 claims extracted from generated code',
    count: 9,
    status: 'success' as const,
    payload: {
      claims: [
        'math module import',
        'sqrt function call',
        'function parameters',
      ],
    },
    timestamp: '2025-01-15T10:20:30Z',
  },
  {
    kind: 'static_analysis' as const,
    summary: 'No syntax errors detected',
    status: 'success' as const,
    payload: {
      errors: [],
      warnings: ['unused variable: temp'],
    },
    timestamp: '2025-01-15T10:20:31Z',
  },
  {
    kind: 'sandbox_execution' as const,
    summary: 'Code executed successfully in 125ms',
    status: 'success' as const,
    payload: {
      output: '3.162277660168379',
      exitCode: 0,
      duration: 125,
    },
    timestamp: '2025-01-15T10:20:32Z',
  },
  {
    kind: 'judge_verdict' as const,
    summary: 'Judge score: 0.95 (Very Low Hallucination)',
    status: 'success' as const,
    payload: {
      score: 0.95,
      reasoning: 'All claims verified, code produces expected output',
    },
    timestamp: '2025-01-15T10:20:33Z',
  },
  {
    kind: 'cove_verification' as const,
    summary: '9/9 claims verified (100%)',
    status: 'success' as const,
    payload: {
      verified_count: 9,
      total_count: 9,
      confidence: 0.98,
    },
    timestamp: '2025-01-15T10:20:34Z',
  },
  {
    kind: 'policy_decision' as const,
    summary: 'Final Decision: ACCEPT (Confidence: 95%)',
    status: 'success' as const,
    payload: {
      decision: 'accept',
      confidence: 0.95,
      reasons: ['Low hallucination', 'All claims verified'],
    },
    timestamp: '2025-01-15T10:20:35Z',
  },
]

export const AllSuccess: Story = {
  args: {
    evidence: sampleEvidence,
    loading: false,
  },
}

export const WithWarning: Story = {
  args: {
    evidence: [
      sampleEvidence[0],
      sampleEvidence[1],
      {
        ...sampleEvidence[2],
        status: 'warning' as const,
        summary: 'Code executed but with warnings',
      },
      sampleEvidence[3],
      sampleEvidence[4],
      sampleEvidence[5],
    ],
    loading: false,
  },
}

export const WithErrors: Story = {
  args: {
    evidence: [
      sampleEvidence[0],
      sampleEvidence[1],
      {
        ...sampleEvidence[2],
        status: 'error' as const,
        summary: 'Sandbox execution failed: Import not found',
      },
      {
        ...sampleEvidence[3],
        status: 'error' as const,
        summary: 'Judge could not evaluate code',
      },
    ],
    loading: false,
  },
}

export const Loading: Story = {
  args: {
    evidence: [
      {
        kind: 'claim_extraction' as const,
        summary: 'Extracting claims...',
        status: 'in_progress' as const,
        payload: {},
      },
      {
        kind: 'static_analysis' as const,
        summary: 'Analyzing code...',
        status: 'pending' as const,
        payload: {},
      },
    ],
    loading: true,
  },
}

export const Empty: Story = {
  args: {
    evidence: [],
    loading: false,
  },
}

export const Repair: Story = {
  args: {
    evidence: [
      ...sampleEvidence,
      {
        kind: 'repair_attempt' as const,
        summary: 'Repair attempt 1: Added missing import',
        count: 1,
        status: 'success' as const,
        payload: {
          fixes_applied: 1,
          retry_attempt: 1,
        },
        timestamp: '2025-01-15T10:20:40Z',
      },
    ],
    loading: false,
  },
}
