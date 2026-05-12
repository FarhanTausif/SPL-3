// cypress/support/commands.ts

Cypress.Commands.add('visitHome', () => {
  cy.visit('/')
})

Cypress.Commands.add('visitMonitor', (id: string) => {
  cy.visit(`/monitor/${id}`)
})

Cypress.Commands.add('enterPrompt', (text: string) => {
  cy.get('textarea[placeholder*="prompt" i], textarea[placeholder*="code" i]').type(text)
})

Cypress.Commands.add('selectLanguage', (language: string) => {
  cy.log(`Language is inferred from prompt; requested helper value was ${language}`)
})

Cypress.Commands.add('startVerification', () => {
  cy.get('button').contains(/start|verify|submit/i).click()
})

declare global {
  namespace Cypress {
    interface Chainable {
      visitHome(): Chainable<void>
      visitMonitor(id: string): Chainable<void>
      enterPrompt(text: string): Chainable<void>
      selectLanguage(language: string): Chainable<void>
      startVerification(): Chainable<void>
    }
  }
}
