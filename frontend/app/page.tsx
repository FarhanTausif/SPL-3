import Link from 'next/link'
import { VerificationForm } from '@/components/VerificationForm'
import { Zap } from 'lucide-react'

export default function Home() {
  return (
    <main className="min-h-screen py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Zap className="w-8 h-8 text-primary" />
            <h1 className="text-4xl font-bold text-gray-900">DeHalu</h1>
          </div>
          <p className="text-xl text-gray-600">
            AI-Powered Code Hallucination Detection & Mitigation
          </p>
          <p className="text-gray-600 mt-2">
            Verify your AI-generated code with 9 verification agents
          </p>
        </div>

        {/* Main Card */}
        <div className="glass p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Start New Verification
          </h2>
          <VerificationForm />
        </div>

        {/* Info Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="glass p-6">
            <h3 className="font-semibold text-gray-900 mb-2">🔍 Detection</h3>
            <p className="text-sm text-gray-600">
              9 AI agents verify your code for hallucinations in real-time
            </p>
          </div>
          <div className="glass p-6">
            <h3 className="font-semibold text-gray-900 mb-2">✨ Mitigation</h3>
            <p className="text-sm text-gray-600">
              Automatic code repair if hallucinations are detected
            </p>
          </div>
          <div className="glass p-6">
            <h3 className="font-semibold text-gray-900 mb-2">📊 Insights</h3>
            <p className="text-sm text-gray-600">
              Detailed evidence and confidence scores
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="mt-12 pt-8 border-t border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">How It Works</h3>
          <ol className="space-y-3 text-gray-700">
            <li className="flex gap-3">
              <span className="font-bold text-primary">1.</span>
              <span>Enter your code generation prompt</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-primary">2.</span>
              <span>Select programming language and verification strictness</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-primary">3.</span>
              <span>Watch real-time verification progress</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-primary">4.</span>
              <span>Review verification results and evidence</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-primary">5.</span>
              <span>Get repaired code if hallucinations were detected</span>
            </li>
          </ol>
        </div>
      </div>
    </main>
  )
}
