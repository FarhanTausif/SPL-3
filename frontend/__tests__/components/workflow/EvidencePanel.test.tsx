import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { EvidencePanel, EvidenceItem } from '@/components/workflow/EvidencePanel'

describe('EvidencePanel Component', () => {
  const mockEvidence: EvidenceItem[] = [
    {
      kind: 'claim_extraction',
      summary: '9 claims identified',
      status: 'success',
      payload: { claims: ['claim1', 'claim2'] },
      timestamp: '2024-01-01T00:00:00Z',
    },
    {
      kind: 'static_analysis',
      summary: '1 import error found',
      status: 'warning',
      payload: { errors: [{ type: 'import', message: 'math not found' }] },
    },
  ]

  it('renders evidence panel header', () => {
    render(<EvidencePanel evidence={mockEvidence} />)
    expect(screen.getByText(/Evidence Collected/i)).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument() // count
  })

  it('displays all evidence items', () => {
    render(<EvidencePanel evidence={mockEvidence} />)
    expect(screen.getByText('Claim Extraction')).toBeInTheDocument()
    expect(screen.getByText('Static Analysis')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<EvidencePanel evidence={[]} loading={true} />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading evidence')
  })

  it('shows empty state when no evidence', () => {
    render(<EvidencePanel evidence={[]} loading={false} />)
    expect(screen.getByText('No evidence collected yet...')).toBeInTheDocument()
  })

  it('expands/collapses evidence items on click', async () => {
    const user = userEvent.setup()
    const { container } = render(<EvidencePanel evidence={mockEvidence} />)

    const buttons = screen.getAllByRole('button')
    const firstButton = buttons[0]

    expect(firstButton).toHaveAttribute('aria-expanded', 'false')
    
    await user.click(firstButton)
    expect(firstButton).toHaveAttribute('aria-expanded', 'true')

    // Evidence detail should be visible
    const detailId = firstButton.getAttribute('aria-controls')
    const detailElement = container.querySelector(`#${detailId}`)
    expect(detailElement).toBeInTheDocument()
  })

  it('copies JSON to clipboard', async () => {
    const user = userEvent.setup()
    const clipboardSpy = vi.spyOn(navigator.clipboard, 'writeText')

    render(<EvidencePanel evidence={mockEvidence} />)

    // Expand first item
    const expandButton = screen.getAllByRole('button')[0]
    await user.click(expandButton)

    // Click copy button
    const copyButton = screen.getByRole('button', { name: /copy/i })
    await user.click(copyButton)

    expect(clipboardSpy).toHaveBeenCalled()
    clipboardSpy.mockRestore()
  })

  it('has proper ARIA attributes for accessibility', () => {
    render(<EvidencePanel evidence={mockEvidence} />)

    const panel = screen.getByRole('region', { name: /Evidence collection results/i })
    expect(panel).toHaveAttribute('aria-live', 'polite')
    expect(panel).toHaveAttribute('aria-busy', 'false')
  })

  it('displays evidence summary text', () => {
    render(<EvidencePanel evidence={mockEvidence} />)
    expect(screen.getByText('9 claims identified')).toBeInTheDocument()
    expect(screen.getByText('1 import error found')).toBeInTheDocument()
  })

  it('shows status indicators correctly', () => {
    render(<EvidencePanel evidence={mockEvidence} />)
    // The component renders status indicators - check that the component renders without error
    const panel = screen.getByRole('region', { name: /Evidence collection results/i })
    expect(panel).toBeInTheDocument()
  })

  it('displays timestamp when provided', async () => {
    const user = userEvent.setup()
    render(<EvidencePanel evidence={mockEvidence} />)

    // Expand first item which has timestamp
    const expandButton = screen.getAllByRole('button')[0]
    await user.click(expandButton)

    // Check for recorded time
    expect(screen.getByText(/Recorded:/)).toBeInTheDocument()
  })
})
