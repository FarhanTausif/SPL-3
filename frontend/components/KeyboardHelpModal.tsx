'use client'

import { memo, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Keyboard } from 'lucide-react'
import { APP_SHORTCUTS, formatShortcut } from '@/hooks/useKeyboardShortcuts'

export const KeyboardHelpModal = memo(function KeyboardHelpModal() {
  const [isOpen, setIsOpen] = useState(false)

  // Listen for help event
  useEffect(() => {
    const handleOpenHelp = () => setIsOpen(true)
    window.addEventListener('open-help', handleOpenHelp)
    return () => window.removeEventListener('open-help', handleOpenHelp)
  }, [])

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/50 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
          />

          {/* Modal */}
          <motion.div
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white dark:bg-slate-900 rounded-lg shadow-2xl max-w-md w-full mx-4 max-h-96 overflow-y-auto"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 sticky top-0 bg-white dark:bg-slate-900">
              <div className="flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                  Keyboard Shortcuts
                </h2>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                aria-label="Close keyboard help"
              >
                <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-3">
              {APP_SHORTCUTS.map((shortcut) => (
                <div key={shortcut.description} className="flex items-center justify-between">
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {shortcut.description}
                  </span>
                  <kbd className="px-2 py-1 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded text-xs font-mono text-slate-900 dark:text-slate-50">
                    {formatShortcut(shortcut)}
                  </kbd>
                </div>
              ))}

              <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400">
                <p>💡 Press <kbd className="inline px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-xs">?</kbd> to open this menu</p>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
})

KeyboardHelpModal.displayName = 'KeyboardHelpModal'
