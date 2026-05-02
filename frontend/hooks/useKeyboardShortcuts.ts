/**
 * Keyboard Shortcuts Hook
 * Provides global keyboard navigation and shortcuts
 */

'use client'

import { useEffect, useCallback } from 'react'

export interface KeyboardShortcut {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  callback: () => void
  description: string
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase()
        const ctrlMatch = (event.ctrlKey || event.metaKey) === (shortcut.ctrl ?? false)
        const shiftMatch = event.shiftKey === (shortcut.shift ?? false)
        const altMatch = event.altKey === (shortcut.alt ?? false)

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          event.preventDefault()
          shortcut.callback()
          break
        }
      }
    },
    [shortcuts]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

/**
 * Global App Shortcuts
 */
export const APP_SHORTCUTS: KeyboardShortcut[] = [
  {
    key: 'k',
    ctrl: true,
    description: 'Focus search',
    callback: () => {
      const searchInput = document.querySelector('input[type="search"]')
      if (searchInput instanceof HTMLInputElement) {
        searchInput.focus()
      }
    },
  },
  {
    key: 'Escape',
    description: 'Close modals/dialogs',
    callback: () => {
      // Close any open modals
      document.querySelectorAll('[role="dialog"]').forEach((dialog) => {
        if (dialog instanceof HTMLElement) {
          const closeBtn = dialog.querySelector('[aria-label*="close"], [aria-label*="Close"]')
          if (closeBtn instanceof HTMLElement) {
            closeBtn.click()
          }
        }
      })
    },
  },
  {
    key: '?',
    description: 'Show help',
    callback: () => {
      // Dispatch custom event for help modal
      window.dispatchEvent(new CustomEvent('open-help'))
    },
  },
  {
    key: 'n',
    ctrl: true,
    description: 'New verification',
    callback: () => {
      window.location.href = '/verify'
    },
  },
  {
    key: 'h',
    ctrl: true,
    description: 'Go to home',
    callback: () => {
      window.location.href = '/'
    },
  },
]

/**
 * Format keyboard shortcut for display
 * e.g., { key: 'k', ctrl: true } → "Ctrl+K"
 */
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = []
  if (shortcut.ctrl) parts.push('Ctrl')
  if (shortcut.alt) parts.push('Alt')
  if (shortcut.shift) parts.push('Shift')
  parts.push(shortcut.key.toUpperCase())
  return parts.join('+')
}

/**
 * Format description for display
 * e.g., "Focus search (Ctrl+K)"
 */
export function formatShortcutDescription(shortcut: KeyboardShortcut): string {
  return `${shortcut.description} (${formatShortcut(shortcut)})`
}
