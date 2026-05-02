/**
 * Performance Constants & Thresholds
 */

export const PERFORMANCE_THRESHOLDS = {
  // Component rendering
  MAX_RENDER_TIME_MS: 16,        // 60fps target
  MAX_INITIAL_PAINT_MS: 3000,    // First paint should be < 3s

  // Network & API
  MAX_API_RESPONSE_TIME_MS: 500,
  POLLING_INTERVAL_MS: 2000,     // Poll every 2 seconds
  QUERY_STALE_TIME_MS: 1000,

  // Debounce/Throttle
  DEBOUNCE_DELAY_MS: 300,
  THROTTLE_DELAY_MS: 100,

  // Intersection Observer
  INTERSECTION_THRESHOLD: 0.1,
  INTERSECTION_ROOT_MARGIN: '50px',
}

export const BUNDLE_SIZE_TARGETS = {
  HOME_PAGE_KB: 120,
  MONITOR_PAGE_KB: 320,
  TOTAL_KB: 400,
  GZIPPED_KB: 100,
}

export const LAZY_LOAD_OPTIONS = {
  threshold: PERFORMANCE_THRESHOLDS.INTERSECTION_THRESHOLD,
  rootMargin: `${PERFORMANCE_THRESHOLDS.INTERSECTION_ROOT_MARGIN}`,
}
