/**
 * Performance optimization utilities
 * - React.memo for component memoization
 * - Dynamic imports for code splitting
 * - Debouncing utilities
 */

/**
 * Debounce hook - delays function execution
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  delayMs: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null

  return function debounced(...args: Parameters<T>) {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => {
      func(...args)
    }, delayMs)
  }
}

/**
 * Throttle hook - limits function execution frequency
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  func: T,
  delayMs: number
): (...args: Parameters<T>) => void {
  let lastCall = 0

  return function throttled(...args: Parameters<T>) {
    const now = Date.now()
    if (now - lastCall >= delayMs) {
      func(...args)
      lastCall = now
    }
  }
}

/**
 * Intersection Observer hook - lazy load components
 */
export function useIntersectionObserver(
  ref: React.RefObject<HTMLElement>,
  options?: IntersectionObserverInit
): boolean {
  const [isVisible, setIsVisible] = React.useState(false)

  React.useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true)
        observer.unobserve(entry.target)
      }
    }, options)

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => {
      observer.disconnect()
    }
  }, [ref, options])

  return isVisible
}

/**
 * Image optimization utilities
 */
export function getOptimizedImageProps(src: string) {
  return {
    src,
    loading: 'lazy' as const,
    decoding: 'async' as const,
  }
}

/**
 * Performance monitoring utility
 */
export function measurePerformance(name: string) {
  const start = performance.now()
  return {
    end: () => {
      const duration = performance.now() - start
      console.log(`[Performance] ${name}: ${duration.toFixed(2)}ms`)
      return duration
    },
  }
}

import React from 'react'
