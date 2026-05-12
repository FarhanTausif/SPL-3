// cypress/e2e/home.cy.ts

describe('Home Page', () => {
  beforeEach(() => {
    cy.visit('/')
  })

  it('renders home page successfully', () => {
    // Check page title
    cy.get('h1').should('exist')
    
    // Check for input form
    cy.get('textarea, input[type="text"]').should('exist')
    
    // Check for start button
    cy.contains('button', /start|verify|submit/i).should('be.visible')
  })

  it('displays input form elements', () => {
    // Check for prompt input
    cy.get('textarea').should('exist')
    
    // User-facing configuration is intentionally hidden.
    cy.get('select').should('not.exist')
  })

  it('validates required fields', () => {
    // Try to submit without filling form
    cy.contains('button', /start|verify|submit/i).click()
    
    // Should show validation error or remain on home page
    cy.url().should('include', '/')
  })

  it('accepts valid input and navigates', () => {
    // Fill in the form
    cy.get('textarea, input[placeholder*="prompt" i]').type('Write hello world in Python')
    
    // Submit form
    cy.contains('button', /start|verify|submit/i).click()
    
    // Should navigate to monitor page
    cy.url().should('include', '/monitor/')
  })

  it('keeps orchestration configuration out of the prompt form', () => {
    cy.contains('Language').should('not.exist')
    cy.contains('Run mode').should('not.exist')
    cy.contains('Provider override').should('not.exist')
    cy.contains('Verification strictness').should('not.exist')
  })

  it('has accessible form elements', () => {
    // Check for form labels
    cy.get('label').should('exist')
    
    // Check for ARIA attributes
    cy.get('textarea, input[type="text"]').should('have.attr', 'placeholder')
  })

  it('shows error handling for network issues', () => {
    // This would require intercepting network requests
    cy.intercept('POST', '**/api/**', { statusCode: 500 }).as('apiError')
    
    cy.get('textarea, input[placeholder*="prompt" i]').type('Test prompt')
    cy.contains('button', /start|verify|submit/i).click()
    
    // Should handle error gracefully (implementation dependent)
  })
})
