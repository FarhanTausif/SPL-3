'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { runApi, CreateRunRequest } from '@/lib/api'
import { useRunStore } from '@/stores/runStore'
import { AlertCircle, Loader } from 'lucide-react'

const LANGUAGES = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
  { value: 'csharp', label: 'C#' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
]

const RISK_LEVELS = [
  { value: 'low', label: 'Low - Fast & simple code' },
  { value: 'medium', label: 'Medium - Standard verification' },
  { value: 'high', label: 'High - Strict verification' },
]

export function VerificationForm() {
  const router = useRouter()
  const setRunId = useRunStore((state) => state.setRunId)

  const [prompt, setPrompt] = useState('')
  const [language, setLanguage] = useState('python')
  const [riskLevel, setRiskLevel] = useState('medium')
  const [validationError, setValidationError] = useState('')

  const mutation = useMutation({
    mutationFn: (request: CreateRunRequest) => runApi.createRun(request),
    onSuccess: (response) => {
      setRunId(response.run_id)
      router.push(`/monitor/${response.run_id}`)
    },
    onError: (error: Error) => {
      setValidationError(error.message)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setValidationError('')

    // Validation
    if (!prompt.trim()) {
      setValidationError('Prompt is required')
      return
    }

    if (prompt.trim().length < 10) {
      setValidationError('Prompt must be at least 10 characters')
      return
    }

    if (prompt.trim().length > 5000) {
      setValidationError('Prompt must not exceed 5000 characters')
      return
    }

    // Submit
    mutation.mutate({
      prompt: prompt.trim(),
      language,
      risk_level: riskLevel,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Prompt Input */}
      <div>
        <label htmlFor="prompt" className="block text-sm font-medium text-gray-900 mb-2">
          Code Generation Prompt
        </label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your code generation prompt. Be specific about requirements, language, and use cases."
          rows={6}
          className="w-full px-4 py-3 rounded-lg border border-gray-300 bg-white text-gray-900 placeholder-gray-500 focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none transition-smooth"
        />
        <div className="mt-2 text-sm text-gray-600">
          {prompt.length}/5000 characters
        </div>
      </div>

      {/* Language Selection */}
      <div>
        <label htmlFor="language" className="block text-sm font-medium text-gray-900 mb-2">
          Programming Language
        </label>
        <select
          id="language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="w-full px-4 py-2 rounded-lg border border-gray-300 bg-white text-gray-900 focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none transition-smooth"
        >
          {LANGUAGES.map((lang) => (
            <option key={lang.value} value={lang.value}>
              {lang.label}
            </option>
          ))}
        </select>
      </div>

      {/* Risk Level Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-3">
          Verification Strictness
        </label>
        <div className="space-y-2">
          {RISK_LEVELS.map((level) => (
            <label key={level.value} className="flex items-center cursor-pointer">
              <input
                type="radio"
                name="riskLevel"
                value={level.value}
                checked={riskLevel === level.value}
                onChange={(e) => setRiskLevel(e.target.value)}
                className="w-4 h-4 text-primary border-gray-300 focus:ring-primary"
              />
              <span className="ml-3 text-sm text-gray-700">{level.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Error Message */}
      {validationError && (
        <div className="flex items-start p-4 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
          <div className="text-sm text-red-800">{validationError}</div>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full px-6 py-3 bg-primary text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-smooth flex items-center justify-center gap-2"
      >
        {mutation.isPending && <Loader className="w-4 h-4 animate-spin" />}
        {mutation.isPending ? 'Creating verification run...' : 'Start Verification'}
      </button>

      {/* Info Text */}
      <p className="text-sm text-gray-600 text-center">
        Your code will be verified by 9 AI agents for hallucinations and potential issues.
      </p>
    </form>
  )
}
