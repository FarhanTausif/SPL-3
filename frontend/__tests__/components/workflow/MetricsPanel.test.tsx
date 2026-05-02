import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MetricsPanel, MetricsData } from '@/components/workflow/MetricsPanel'

describe('MetricsPanel Component', () => {
  const mockMetrics: Partial<MetricsData> = {
    hallucination_risk_score: 0.25,
    confidence: 0.85,
    verification_progress: {
      claims_verified: 8,
      claims_total: 9,
      static_passed: true,
      sandbox_passed: true,
      judge_score: 0.95,
      cove_verified_percent: 89,
    },
    timing: {
      generation_ms: 500,
      claims_ms: 100,
      static_ms: 50,
      sandbox_ms: 10,
      judge_ms: 150,
      cove_ms: 200,
      policy_ms: 5,
    },
  }

  it('renders hallucination risk gauge', () => {
    render(<MetricsPanel metrics={mockMetrics} />)
    expect(screen.getByText(/HALLUCINATION RISK/i)).toBeInTheDocument()
    expect(screen.getByText('25%')).toBeInTheDocument()
  })

  it('displays confidence percentage', () => {
    render(<MetricsPanel metrics={mockMetrics} />)
    expect(screen.getByText(/CONFIDENCE/i)).toBeInTheDocument()
    expect(screen.getByText('85.0%')).toBeInTheDocument()
  })

  it('shows correct risk level classification', () => {
    render(<MetricsPanel metrics={mockMetrics} />)
    expect(screen.getByText('LOW')).toBeInTheDocument()
  })

  it('displays verification progress data', () => {
    render(<MetricsPanel metrics={mockMetrics} />)
    // Check for claims verified count (8/9)
    expect(screen.getByText(/8\s*\/\s*9/)).toBeInTheDocument()
  })

  it('shows timing breakdown', () => {
    render(<MetricsPanel metrics={mockMetrics} />)
    expect(screen.getByText(/TIMING BREAKDOWN/i)).toBeInTheDocument()
  })

  it('displays policy decision badge', () => {
    render(<MetricsPanel metrics={mockMetrics} policyDecision="accept" />)
    // The component renders FINAL DECISION instead of POLICY DECISION
    expect(screen.getByText(/FINAL DECISION/i)).toBeInTheDocument()
    expect(screen.getByText(/ACCEPT/i)).toBeInTheDocument()
  })

  it('handles high risk score appropriately', () => {
    const highRiskMetrics: Partial<MetricsData> = {
      ...mockMetrics,
      hallucination_risk_score: 0.85,
    }
    render(<MetricsPanel metrics={highRiskMetrics} />)
    expect(screen.getByText('85%')).toBeInTheDocument()
    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })

  it('handles medium risk score appropriately', () => {
    const mediumRiskMetrics: Partial<MetricsData> = {
      ...mockMetrics,
      hallucination_risk_score: 0.55,
    }
    render(<MetricsPanel metrics={mediumRiskMetrics} />)
    expect(screen.getByText('55%')).toBeInTheDocument()
    expect(screen.getByText('MEDIUM')).toBeInTheDocument()
  })

  it('has proper ARIA labels for accessibility', () => {
    render(<MetricsPanel metrics={mockMetrics} />)
    
    const region = screen.getByRole('region', { name: /Verification metrics/i })
    expect(region).toBeInTheDocument()
  })

  it('uses role=img for gauge with descriptive aria-label', () => {
    render(<MetricsPanel metrics={mockMetrics} />)
    
    const gauge = screen.getByRole('img', { name: /Hallucination risk gauge/i })
    expect(gauge).toBeInTheDocument()
  })

  it('displays alerts when provided', () => {
    const metricsWithAlerts: Partial<MetricsData> = {
      ...mockMetrics,
      alerts: ['Import error in line 5', 'Syntax warning on line 12'],
    }
    render(<MetricsPanel metrics={metricsWithAlerts} />)
    expect(screen.getByText(/Import error/)).toBeInTheDocument()
    expect(screen.getByText(/Syntax warning/)).toBeInTheDocument()
  })

  it('defaults missing values gracefully', () => {
    const minimalMetrics: Partial<MetricsData> = {}
    render(<MetricsPanel metrics={minimalMetrics} />)
    
    // Should render without errors
    expect(screen.getByText(/HALLUCINATION RISK/i)).toBeInTheDocument()
    expect(screen.getByText(/CONFIDENCE/i)).toBeInTheDocument()
  })

  it('displays different policy decisions', () => {
    const { rerender } = render(<MetricsPanel metrics={mockMetrics} policyDecision="accept" />)
    expect(screen.getByText(/ACCEPT/i)).toBeInTheDocument()

    rerender(<MetricsPanel metrics={mockMetrics} policyDecision="warn" />)
    expect(screen.getByText(/WARN/i)).toBeInTheDocument()

    rerender(<MetricsPanel metrics={mockMetrics} policyDecision="reject" />)
    expect(screen.getByText(/REJECT/i)).toBeInTheDocument()
  })
})
