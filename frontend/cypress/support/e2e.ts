// cypress/support/e2e.ts

import './commands'

// Disable uncaught exception handling for specific errors
Cypress.on('uncaught:exception', (err) => {
  // Ignore ResizeObserver errors
  if (err.message.includes('ResizeObserver loop limit exceeded')) {
    return false
  }
  // Return true to let Cypress fail the test
  return true
})
