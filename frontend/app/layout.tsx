'use client'

import React, { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ToastContainer, useToast } from '@/components/ToastContainer'
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

  return (
    <html lang="en">
      <body className="bg-background">
        <ErrorBoundary fallback={(error, retry) => (
          <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center px-4">
            <div className="bg-white rounded-lg border border-red-200 shadow-lg p-6 max-w-md w-full">
              <h2 className="text-lg font-semibold text-slate-900">Unexpected Error</h2>
              <p className="text-sm text-slate-600 mt-2">{error.message}</p>
              <button
                onClick={retry}
                className="mt-4 w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium"
              >
                Try Again
              </button>
            </div>
          </div>
        )}>
          <QueryClientProvider client={queryClient}>
            <div className="min-h-screen">
              {children}
            </div>
            <ToastContainer toasts={toasts} onRemove={removeToast} />
          </QueryClientProvider>
        </ErrorBoundary>
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
