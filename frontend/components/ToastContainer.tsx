'use client'

import { useState } from 'react'
import { AlertCircle, CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export type ToastType = 'error' | 'success' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  message: string
  description?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

const iconMap: Record<ToastType, React.ReactNode> = {
  error: <AlertCircle className="w-5 h-5" />,
  success: <CheckCircle2 className="w-5 h-5" />,
  warning: <AlertTriangle className="w-5 h-5" />,
  info: <Info className="w-5 h-5" />,
}

const colorMap: Record<ToastType, string> = {
  error: 'bg-red-50 border-red-200 text-red-900',
  success: 'bg-green-50 border-green-200 text-green-900',
  warning: 'bg-amber-50 border-amber-200 text-amber-900',
  info: 'bg-blue-50 border-blue-200 text-blue-900',
}

const iconColorMap: Record<ToastType, string> = {
  error: 'text-red-600',
  success: 'text-green-600',
  warning: 'text-amber-600',
  info: 'text-blue-600',
}

interface ToastContextType {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => string
  removeToast: (id: string) => void
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = (toast: Omit<Toast, 'id'>): string => {
    const id = Date.now().toString()
    const fullToast: Toast = { ...toast, id, duration: toast.duration ?? 5000 }

    setToasts(prev => [...prev, fullToast])

    if (fullToast.duration && fullToast.duration > 0) {
      setTimeout(() => removeToast(id), fullToast.duration)
    }

    return id
  }

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  return { toasts, addToast, removeToast }
}

interface ToastContainerProps {
  toasts: Toast[]
  onRemove: (id: string) => void
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-md space-y-2" role="region" aria-label="Notifications">
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className={`border rounded-lg p-4 shadow-lg flex items-start gap-3 ${colorMap[toast.type]}`}
            role="alert"
            aria-live="polite"
          >
            <div className={`flex-shrink-0 ${iconColorMap[toast.type]}`}>
              {iconMap[toast.type]}
            </div>

            <div className="flex-1">
              <h3 className="font-semibold text-sm">{toast.message}</h3>
              {toast.description && (
                <p className="text-sm opacity-90 mt-1">{toast.description}</p>
              )}
              {toast.action && (
                <button
                  onClick={() => {
                    toast.action?.onClick()
                    onRemove(toast.id)
                  }}
                  className="text-sm font-medium mt-2 hover:opacity-75 transition-opacity"
                >
                  {toast.action.label}
                </button>
              )}
            </div>

            <button
              onClick={() => onRemove(toast.id)}
              className="flex-shrink-0 hover:opacity-75 transition-opacity"
              aria-label="Close notification"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
