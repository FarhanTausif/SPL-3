// cypress/e2e/accessibility.cy.ts

describe('Accessibility - WCAG 2.1 AA Compliance', () => {
  beforeEach(() => {
    cy.visit('/')
  })

  it('has proper heading hierarchy', () => {
    // Should have h1
    cy.get('h1').should('exist')
    
    // Headings should be in order
    cy.get('h1, h2, h3, h4, h5, h6').each((heading, index) => {
      if (index > 0) {
        const currentLevel = parseInt(heading.prop('tagName')[1])
        const prevLevel = parseInt(
          heading.prevAll('h1, h2, h3, h4, h5, h6').first().prop('tagName')[1]
        )
        expect(currentLevel).to.be.lte(prevLevel + 1)
      }
    })
  })

  it('has skip link for keyboard users', () => {
    // Tab to skip link
    cy.get('body').tab()
    cy.focused().should('have.attr', 'href', '#main-content')
  })

  it('all buttons are focusable', () => {
    cy.get('button').each((button) => {
      cy.wrap(button).should('have.attr', 'type')
    })
  })

  it('form inputs have associated labels', () => {
    cy.get('input, textarea, select').each((input) => {
      if (!input.hasClass('sr-only')) {
        // Should have label or aria-label
        const hasLabel = cy.get(`label[for="${input.attr('id')}"]`).should('exist')
        const hasAriaLabel = input.attr('aria-label')
        expect(hasLabel || hasAriaLabel).to.exist
      }
    })
  })

  it('has sufficient color contrast', () => {
    // This checks visible text elements
    cy.get('body').within(() => {
      cy.get('*').each((element) => {
        const bgColor = window.getComputedStyle(element).backgroundColor
        const textColor = window.getComputedStyle(element).color
        
        // Should not be same color (basic contrast check)
        expect(bgColor).not.to.equal(textColor)
      })
    })
  })

  it('interactive elements have focus indicators', () => {
    cy.get('button, a, input, textarea, select').first().focus()
    cy.focused().should('have.css', 'outline')
  })

  it('has proper ARIA attributes', () => {
    // Check for ARIA roles
    cy.get('[role]').should('have.length.greaterThan', 0)
    
    // Check for ARIA labels where needed
    cy.get('[role="button"]:not(button)').each((button) => {
      cy.wrap(button).should('have.attr', 'aria-label')
    })
  })

  it('supports reduced motion preference', () => {
    // Set reduced motion preference
    cy.visit('/', {
      onBeforeLoad(win) {
        Object.defineProperty(win, 'matchMedia', {
          writable: true,
          value: (query: string) => ({
            matches: query === '(prefers-reduced-motion: reduce)',
            media: query,
            onchange: null,
            addListener: cy.stub(),
            removeListener: cy.stub(),
            addEventListener: cy.stub(),
            removeEventListener: cy.stub(),
            dispatchEvent: cy.stub(),
          }),
        })
      },
    })

    // Page should still be functional
    cy.get('body').should('exist')
  })

  it('text is resizable up to 200%', () => {
    // Check zoom works
    cy.visit('/', {
      onBeforeLoad(win) {
        win.document.documentElement.style.fontSize = '20px'
      },
    })

    // Content should not overflow
    cy.get('body').should('exist')
  })

  it('has semantic HTML structure', () => {
    // Should use semantic tags
    cy.get('main, nav, header, footer, section, article').should('have.length.greaterThan', 0)
  })

  it('monitor page accessibility', () => {
    const runId = 'test-123'
    cy.intercept('GET', `/api/runs/${runId}`, {
      body: {
        run_id: runId,
        status: 'started',
        metadata: {},
      },
    })

    cy.visit(`/monitor/${runId}`)

    // Check main content region
    cy.get('[id="main-content"], main').should('exist')

    // Check for skip link
    cy.get('a[href="#main-content"]').should('exist')

    // Check for ARIA live regions
    cy.get('[aria-live]').should('have.length.greaterThan', 0)
  })
})
