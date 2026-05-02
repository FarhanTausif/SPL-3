// lib/errorHandler.ts

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public message: string,
    public details?: Record<string, unknown>
  ) {
    super(message)
    this.name = 'ApiError'
  }

  static isApiError(error: unknown): error is ApiError {
    return error instanceof ApiError
  }
}

export class ValidationError extends Error {
  constructor(
    public field: string,
    public message: string
  ) {
    super(`${field}: ${message}`)
    this.name = 'ValidationError'
  }

  static isValidationError(error: unknown): error is ValidationError {
    return error instanceof ValidationError
  }
}

export class NetworkError extends Error {
  constructor(message: string = 'Network connection failed') {
    super(message)
    this.name = 'NetworkError'
  }

  static isNetworkError(error: unknown): error is NetworkError {
    return error instanceof NetworkError
  }
}

/**
 * Parse error response from API
 */
export function parseApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }

  if (error instanceof NetworkError) {
    return new ApiError(0, error.message)
  }

  if (error instanceof Response) {
    return new ApiError(
      error.status,
      error.statusText || 'An error occurred',
      { response: error }
    )
  }

  if (error instanceof Error) {
    if (error.message.includes('fetch')) {
      return new ApiError(0, error.message)
    }
    return new ApiError(500, error.message)
  }

  return new ApiError(500, 'An unknown error occurred')
}

/**
 * Get user-friendly error message
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ValidationError) {
    return `Invalid ${error.field}: ${error.message}`
  }

  if (error instanceof NetworkError) {
    return 'Network connection failed. Please check your internet connection.'
  }

  if (error instanceof ApiError) {
    switch (error.statusCode) {
      case 400:
        return 'Invalid request. Please check your input.'
      case 401:
        return 'Authentication required. Please log in.'
      case 403:
        return 'You do not have permission to perform this action.'
      case 404:
        return 'The requested resource was not found.'
      case 429:
        return 'Too many requests. Please try again later.'
      case 500:
        return 'Server error. Please try again later.'
      case 503:
        return 'Service unavailable. Please try again later.'
      default:
        return error.message || 'An error occurred. Please try again.'
    }
  }

  if (error instanceof Error) {
    return error.message || 'An unexpected error occurred.'
  }

  return 'An unexpected error occurred. Please try again.'
}

/**
 * Determine if error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  if (error instanceof ApiError) {
    // Retry on network errors and server errors
    return error.statusCode === 0 || error.statusCode >= 500
  }

  if (error instanceof NetworkError) {
    return true
  }

  return false
}

/**
 * Retry function with exponential backoff
 */
export async function retry<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  delayMs: number = 1000
): Promise<T> {
  let lastError: unknown

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error

      if (!isRetryableError(error) || attempt === maxAttempts) {
        throw error
      }

      // Exponential backoff
      const delay = delayMs * Math.pow(2, attempt - 1)
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }

  throw lastError
}
