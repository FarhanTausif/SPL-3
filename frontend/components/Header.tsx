'use client'

import { ThemeToggle } from '@/components/ThemeToggle'
import { memo } from 'react'

export const Header = memo(function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-50">DeHalu</h1>
          <span className="text-xs px-2 py-1 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200 font-medium">
            Hallucination Detector
          </span>
        </div>

        <nav className="flex items-center gap-4">
          <ThemeToggle />
        </nav>
      </div>
    </header>
  )
})

Header.displayName = 'Header'
