import type { Meta, StoryObj } from '@storybook/react'
import { MetricsPanel } from '@/components/workflow/MetricsPanel'

const meta = {
  title: 'Workflow/MetricsPanel',
  component: MetricsPanel,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'Displays verification metrics including hallucination risk, confidence, and timing breakdown.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    policyDecision: {
      options: ['accept', 'warn', 'repair', 'reject'],
      control: { type: 'radio' },
      description: 'Final policy decision',
    },
  },
} satisfies Meta<typeof MetricsPanel>

export default meta
type Story = StoryObj<typeof meta>

const baseMetrics = {
  hallucination_risk_score: 0.15,
  confidence: 0.92,
  verification_progress: {
    claims_verified: 9,
    claims_total: 9,
    static_passed: true,
    sandbox_passed: true,
    judge_score: 0.95,
    cove_verified_percent: 100,
  },
  timing: {
    generation_ms: 500,
    claims_ms: 100,
    static_ms: 50,
    sandbox_ms: 10,
    judge_ms: 13,
    cove_ms: 94,
    policy_ms: 5,
  },
}

export const LowRisk: Story = {
  args: {
    metrics: baseMetrics,
    policyDecision: 'accept',
  },
}

export const MediumRisk: Story = {
  args: {
    metrics: {
      ...baseMetrics,
      hallucination_risk_score: 0.52,
      confidence: 0.68,
    },
    policyDecision: 'warn',
  },
}

export const HighRisk: Story = {
  args: {
    metrics: {
      ...baseMetrics,
      hallucination_risk_score: 0.85,
      confidence: 0.25,
      verification_progress: {
        ...baseMetrics.verification_progress,
        judge_score: 0.3,
        cove_verified_percent: 50,
      },
    },
    policyDecision: 'reject',
  },
}

export const RepairAttempt: Story = {
  args: {
    metrics: {
      ...baseMetrics,
      hallucination_risk_score: 0.45,
      confidence: 0.55,
    },
    policyDecision: 'repair',
  },
}

export const PartialVerification: Story = {
  args: {
    metrics: {
      hallucination_risk_score: 0.6,
      confidence: 0.5,
      verification_progress: {
        claims_verified: 6,
        claims_total: 9,
        static_passed: true,
        sandbox_passed: false,
        judge_score: 0.5,
        cove_verified_percent: 67,
      },
      timing: {
        generation_ms: 500,
        claims_ms: 100,
        static_ms: 50,
        sandbox_ms: 200,
        judge_ms: 13,
        cove_ms: 94,
        policy_ms: 5,
      },
    },
    policyDecision: 'warn',
  },
}
