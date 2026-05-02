import type { Meta, StoryObj } from '@storybook/react'
import { ThemeToggle } from '@/components/ThemeToggle'
import { ThemeProvider } from '@/lib/theme'

const meta = {
  title: 'Components/ThemeToggle',
  component: ThemeToggle,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'Theme switcher component supporting light, dark, and system modes.',
      },
    },
  },
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <ThemeProvider>
        <Story />
      </ThemeProvider>
    ),
  ],
} satisfies Meta<typeof ThemeToggle>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {}

export const InHeader: Story = {
  render: () => (
    <div className="w-full bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 p-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">DeHalu</h1>
        <ThemeToggle />
      </div>
    </div>
  ),
}
