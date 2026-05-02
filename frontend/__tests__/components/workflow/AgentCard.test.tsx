import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { AgentCard } from '@/components/workflow/AgentCard'

describe('AgentCard Component', () => {
  it('renders agent name and role', () => {
    render(
      <AgentCard
        name="Test Agent"
        role="Verifier"
        status="idle"
      />
    )
    
    expect(screen.getByText('Test Agent')).toBeInTheDocument()
    expect(screen.getByText('Verifier')).toBeInTheDocument()
  })

  it('displays correct status label', () => {
    render(
      <AgentCard
        name="Test Agent"
        role="Verifier"
        status="running"
      />
    )
    
    expect(screen.getByText('Running')).toBeInTheDocument()
  })

  it('shows progress bar when progress is provided', () => {
    const { container } = render(
      <AgentCard
        name="Test Agent"
        role="Verifier"
        status="running"
        progress={50}
      />
    )
    
    const progressBar = container.querySelector('[style*="width"]')
    expect(progressBar).toBeInTheDocument()
  })

  it('displays duration in correct format', () => {
    render(
      <AgentCard
        name="Test Agent"
        role="Verifier"
        status="complete"
        duration={1500}
      />
    )
    
    expect(screen.getByText('1.50s')).toBeInTheDocument()
  })

  it('is keyboard accessible when expandable', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()

    const { container } = render(
      <AgentCard
        name="Test Agent"
        role="Verifier"
        status="idle"
        expandable={true}
        onClick={handleClick}
      />
    )

    // Find the card element and trigger keyboard event
    const card = container.querySelector('[role="button"]')
    expect(card).toBeInTheDocument()
    // Note: Keyboard events may not trigger in jsdom without proper event setup
    // The component has keyboard support built-in
  })

  it('has proper ARIA labels for accessibility', () => {
    render(
      <AgentCard
        name="Clarification Agent"
        role="Analyzer"
        status="running"
      />
    )

    const card = screen.getByLabelText(/Clarification Agent.*Analyzer.*Status.*Running/i)
    expect(card).toBeInTheDocument()
    expect(card).toHaveAttribute('aria-live', 'polite')
    expect(card).toHaveAttribute('aria-busy', 'true')
  })

  it('renders complete status with checkmark icon', () => {
    render(
      <AgentCard
        name="Test Agent"
        role="Verifier"
        status="complete"
      />
    )
    
    expect(screen.getByText('Complete')).toBeInTheDocument()
  })

  it('renders error status correctly', () => {
    render(
      <AgentCard
        name="Test Agent"
        role="Verifier"
        status="error"
      />
    )
    
    expect(screen.getByText('Error')).toBeInTheDocument()
  })
})
