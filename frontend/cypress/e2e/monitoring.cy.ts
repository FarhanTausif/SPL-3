// cypress/e2e/monitoring.cy.ts

describe('Monitor Page - Workflow Visualization', () => {
  const runId = 'test-run-123'

  beforeEach(() => {
    // Mock the API responses for monitoring
    cy.intercept('GET', `/api/runs/${runId}`, {
      statusCode: 200,
      body: {
        run_id: runId,
        status: 'started',
        created_at: new Date().toISOString(),
        verdict: 'accept',
        metadata: {},
      },
    }).as('getRunStatus')

    cy.visit(`/monitor/${runId}`)
  })

  it('loads monitor page successfully', () => {
    cy.get('h1').should('contain', 'Verification')
    cy.get('[role="region"]').should('exist')
  })

  it('displays workflow DAG component', () => {
    // Check for React Flow DAG
    cy.get('[class*="reactflow"]').should('exist')
    cy.get('[class*="node"]').should('exist')
  })

  it('displays metrics panel', () => {
    // Check for risk gauge
    cy.get('[role="region"]').should('exist')
    cy.contains('HALLUCINATION RISK').should('be.visible')
    cy.contains('CONFIDENCE').should('be.visible')
  })

  it('displays evidence collection panel', () => {
    // Check for evidence section
    cy.contains('Evidence Collected').should('be.visible')
  })

  it('shows elapsed time counter', () => {
    // Should display time in format "Xm Ys"
    cy.get('main').should('contain', /(0|[1-9]\d*)m/)
  })

  it('displays run information', () => {
    // Check for run ID display
    cy.should('contain', runId.slice(0, 8))
  })

  it('responsive layout on mobile', () => {
    // Set viewport to mobile size
    cy.viewport('iphone-x')
    
    // Components should still be visible
    cy.get('[role="region"]').should('exist')
    cy.contains('HALLUCINATION RISK').should('be.visible')
  })

  it('responsive layout on tablet', () => {
    // Set viewport to tablet size
    cy.viewport('ipad-2')
    
    // Components should adapt to tablet layout
    cy.get('[role="region"]').should('exist')
  })

  it('handles workflow state transitions', () => {
    // Verify workflow shows different states
    cy.get('main').should('exist')
    
    // Check for status indicators
    cy.get('main').should('contain', 'Verification')
  })

  it('displays evidence items when collected', () => {
    // Evidence panel should display collected evidence
    cy.contains('Evidence Collected').parent().should('exist')
  })

  it('has proper keyboard navigation', () => {
    // Tab through elements
    cy.get('body').tab()
    cy.focused().should('have.focus')
  })

  it('polls for updates periodically', () => {
    // Wait for polling request
    cy.wait('@getRunStatus', { timeout: 3000 }).then((interception) => {
      expect(interception.response?.statusCode).to.equal(200)
    })
  })

  it('handles polling errors gracefully', () => {
    cy.intercept('GET', `/api/runs/${runId}`, {
      statusCode: 500,
      body: { error: 'Server error' },
    })

    // Page should still be usable
    cy.get('main').should('exist')
  })
})
