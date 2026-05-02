import type { Meta, StoryObj } from '@storybook/react'
import { AgentCard } from '@/components/workflow/AgentCard'

const meta = {
  title: 'Workflow/AgentCard',
  component: AgentCard,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'Displays an agent status card with progress, duration, and state visualization.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    status: {
      options: ['idle', 'running', 'complete', 'error'],
      control: { type: 'radio' },
      description: 'Agent current status',
    },
    progress: {
      control: { type: 'range', min: 0, max: 100, step: 10 },
      description: 'Completion progress (0-100%)',
    },
    expandable: {
      control: 'boolean',
      description: 'Whether the card is clickable/expandable',
    },
  },
} satisfies Meta<typeof AgentCard>

export default meta
type Story = StoryObj<typeof meta>

export const Idle: Story = {
  args: {
    name: 'Clarification',
    role: 'Analyzer',
    status: 'idle',
    expandable: true,
  },
}

export const Running: Story = {
  args: {
    name: 'Code Generation',
    role: 'Generator',
    status: 'running',
    progress: 45,
    expandable: true,
  },
}

export const Complete: Story = {
  args: {
    name: 'Static Analysis',
    role: 'Analyzer',
    status: 'complete',
    progress: 100,
    duration: 250,
    expandable: true,
  },
}

export const Error: Story = {
  args: {
    name: 'Judge Verification',
    role: 'Verifier',
    status: 'error',
    progress: 75,
    expandable: true,
  },
}

export const WithDuration: Story = {
  args: {
    name: 'Sandbox Execution',
    role: 'Executor',
    status: 'complete',
    progress: 100,
    duration: 125,
    expandable: true,
  },
}

export const NonExpandable: Story = {
  args: {
    name: 'CoVE Verification',
    role: 'Verifier',
    status: 'running',
    progress: 60,
    expandable: false,
  },
}
