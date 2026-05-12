'use client'

import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/lib/theme'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ToastContainer, useToast } from '@/components/ToastContainer'
import { KeyboardHelpModal } from '@/components/KeyboardHelpModal'
import { useKeyboardShortcuts, APP_SHORTCUTS } from '@/hooks/useKeyboardShortcuts'
import './globals.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000,
      retry: 1,
    },
  },
})

function RootLayoutContent({
  children,
}: {
  children: React.ReactNode
}) {
  const { toasts, addToast, removeToast } = useToast()

  // Register global keyboard shortcuts
  useKeyboardShortcuts(APP_SHORTCUTS)

  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-background font-sans">
        <ThemeProvider>
          <ErrorBoundary fallback={(error, retry) => (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center px-4">
              <div className="bg-white dark:bg-slate-800 rounded-lg border border-red-200 dark:border-red-900 shadow-lg p-6 max-w-md w-full">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Unexpected Error</h2>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">{error.message}</p>
                <button
                  onClick={retry}
                  className="mt-4 w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white rounded font-medium transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}>
            <QueryClientProvider client={queryClient}>
              <KeyboardHelpModal />
              <div className="min-h-screen">
                {children}
              </div>
              <ToastContainer toasts={toasts} onRemove={removeToast} />
            </QueryClientProvider>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  )
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <RootLayoutContent>{children}</RootLayoutContent>
}
