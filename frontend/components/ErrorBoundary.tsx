'use client'

import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import Link from 'next/link'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: (error: Error, retry: () => void) => ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error details
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError && this.state.error) {
      return (
        this.props.fallback?.(this.state.error, () => 
          this.setState({ hasError: false, error: null })
        ) || (
          <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center px-4">
            <div className="bg-white rounded-lg border border-red-200 shadow-lg p-6 max-w-md w-full">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-1" />
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-slate-900">Something went wrong</h2>
                  <p className="text-sm text-slate-600 mt-1">
                    An unexpected error occurred. Please try again or contact support.
                  </p>
                  <p className="text-xs text-slate-500 mt-2 font-mono break-words">
                    {this.state.error.message}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => this.setState({ hasError: false, error: null })}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition-colors"
                  aria-label="Try again"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </button>
                <Link
                  href="/"
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-900 rounded font-medium transition-colors"
                >
                  <Home className="w-4 h-4" />
                  Home
                </Link>
              </div>
            </div>
          </div>
        )
      )
    }

    return this.props.children
  }
}
