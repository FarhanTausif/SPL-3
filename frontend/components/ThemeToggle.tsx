'use client'

import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/lib/theme'
import { memo } from 'react'

export const ThemeToggle = memo(function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme()

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme)
  }

  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
      {/* Light Mode Button */}
      <button
        onClick={() => handleThemeChange('light')}
        className={`p-2 rounded transition-colors ${
          theme === 'light'
            ? 'bg-white dark:bg-slate-700 shadow-sm'
            : 'hover:bg-slate-200 dark:hover:bg-slate-700'
        }`}
        aria-label="Light mode"
        title="Light Mode"
      >
        <Sun className="w-4 h-4 text-amber-500" />
      </button>

      {/* Dark Mode Button */}
      <button
        onClick={() => handleThemeChange('dark')}
        className={`p-2 rounded transition-colors ${
          theme === 'dark'
            ? 'bg-white dark:bg-slate-700 shadow-sm'
            : 'hover:bg-slate-200 dark:hover:bg-slate-700'
        }`}
        aria-label="Dark mode"
        title="Dark Mode"
      >
        <Moon className="w-4 h-4 text-slate-700 dark:text-blue-400" />
      </button>

      {/* System Mode Button */}
      <button
        onClick={() => handleThemeChange('system')}
        className={`px-2 py-1 text-xs rounded transition-colors font-medium ${
          theme === 'system'
            ? 'bg-white dark:bg-slate-700 shadow-sm'
            : 'hover:bg-slate-200 dark:hover:bg-slate-700'
        }`}
        aria-label="System theme"
        title="System Theme"
      >
        Auto
      </button>
    </div>
  )
})

ThemeToggle.displayName = 'ThemeToggle'
