'use client';

import { motion } from 'framer-motion';
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { AlertCircle, CheckCircle2, AlertTriangle } from 'lucide-react';

export interface MetricsData {
  hallucination_risk_score: number; // 0-1
  confidence: number; // 0-1
  verification_progress: {
    claims_verified: number;
    claims_total: number;
    static_passed: boolean;
    sandbox_passed: boolean;
    judge_score: number; // 0-1
    cove_verified_percent: number; // 0-100
  };
  timing: {
    generation_ms: number;
    claims_ms: number;
    static_ms: number;
    sandbox_ms: number;
    judge_ms: number;
    cove_ms: number;
    policy_ms: number;
  };
  alerts?: string[];
}

interface MetricsPanelProps {
  metrics: Partial<MetricsData>;
  policyDecision?: 'accept' | 'warn' | 'repair' | 'reject';
}

export function MetricsPanel({ metrics, policyDecision = 'accept' }: MetricsPanelProps) {
  const riskScore = metrics.hallucination_risk_score ?? 0.5;
  const confidence = metrics.confidence ?? 0;
  const verification = metrics.verification_progress || {};
  const timing = metrics.timing || {};

  // Risk level classification
  const getRiskLevel = (score: number) => {
    if (score >= 0.7) return { level: 'HIGH', color: '#ef4444', bg: 'bg-red-50' };
    if (score >= 0.4) return { level: 'MEDIUM', color: '#f59e0b', bg: 'bg-amber-50' };
    return { level: 'LOW', color: '#10b981', bg: 'bg-green-50' };
  };

  const riskLevel = getRiskLevel(riskScore);

  // Progress data
  const progressData = [
    { name: 'Claims', value: (verification as any)?.claims_verified ?? 0, total: (verification as any)?.claims_total ?? 1 },
    { name: 'Static', value: (verification as any)?.static_passed ? 1 : 0, total: 1 },
    { name: 'Sandbox', value: (verification as any)?.sandbox_passed ? 1 : 0, total: 1 },
  ];

  // Timing data
  const timingData = [
    { name: 'Generation', value: (timing as any)?.generation_ms ?? 0 },
    { name: 'Claims', value: (timing as any)?.claims_ms ?? 0 },
    { name: 'Static', value: (timing as any)?.static_ms ?? 0 },
    { name: 'Sandbox', value: (timing as any)?.sandbox_ms ?? 0 },
    { name: 'Judge', value: (timing as any)?.judge_ms ?? 0 },
    { name: 'CoVE', value: (timing as any)?.cove_ms ?? 0 },
    { name: 'Policy', value: (timing as any)?.policy_ms ?? 0 },
  ].filter((item) => item.value > 0);

  const totalTime = Object.values(timing as any).reduce((a: any, b: any) => (a || 0) + (b || 0), 0) || 1;

  return (
    <motion.div
      className="flex flex-col h-full bg-gradient-to-br from-slate-50 to-white rounded-lg border border-slate-200 overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 bg-white">
        <h3 className="font-semibold text-sm text-slate-900">📊 Metrics & Analysis</h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" role="region" aria-label="Verification metrics and risk assessment">
        {/* Risk Gauge */}
        <motion.div
          className={`p-4 rounded-lg border-2 ${riskLevel.bg} border-slate-200`}
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
          role="img"
          aria-label={`Hallucination risk gauge showing ${(riskScore * 100).toFixed(0)}% risk level: ${riskLevel.level}`}
        >
          <div className="text-center">
            <p className="text-xs font-medium text-slate-700 mb-2">HALLUCINATION RISK</p>

            {/* Gauge Circle */}
            <motion.div className="relative mx-auto w-24 h-24 rounded-full border-4 border-slate-300 flex items-center justify-center overflow-hidden">
              <motion.div
                className="absolute inset-0 rounded-full"
                style={{
                  background: `conic-gradient(${riskLevel.color} 0deg, ${riskLevel.color} ${
                    riskScore * 360
                  }deg, #e2e8f0 ${riskScore * 360}deg)`,
                }}
                aria-hidden="true"
              />
              <motion.div className="relative bg-white w-20 h-20 rounded-full flex flex-col items-center justify-center">
                <motion.span
                  className="text-2xl font-bold"
                  style={{ color: riskLevel.color }}
                  animate={{
                    scale: [1, 1.05, 1],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                  }}
                  aria-hidden="true"
                >
                  {(riskScore * 100).toFixed(0)}%
                </motion.span>
                <span className="text-xs font-medium" style={{ color: riskLevel.color }} aria-hidden="true">
                  {riskLevel.level}
                </span>
              </motion.div>
            </motion.div>

            {/* Confidence */}
            <div className="mt-3 pt-3 border-t border-slate-300">
              <p className="text-xs text-slate-600 mb-1" id="confidence-label">CONFIDENCE</p>
              <motion.div className="w-full bg-slate-300 rounded-full h-2 overflow-hidden" aria-hidden="true">
                <motion.div
                  className="h-full bg-gradient-to-r from-blue-500 to-blue-600"
                  initial={{ width: 0 }}
                  animate={{ width: `${(confidence * 100) || 0}%` }}
                  transition={{ duration: 0.5 }}
                />
              </motion.div>
              <p className="text-xs font-medium text-slate-700 mt-1" aria-labelledby="confidence-label">
                {(confidence * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </motion.div>

        {/* Verification Progress */}
        <motion.div
          className="p-4 rounded-lg bg-white border border-slate-200"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <p className="text-xs font-semibold text-slate-700 mb-3">VERIFICATION STAGES</p>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">Claims Verified</span>
              <span className="font-semibold text-slate-900">
                {(verification as any).claims_verified ?? 0}/{(verification as any).claims_total ?? 1}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">Static Analysis</span>
              <span className="flex items-center gap-1">
                {(verification as any).static_passed ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span className="text-green-700 font-medium">PASSED</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-red-500" />
                    <span className="text-red-700 font-medium">FAILED</span>
                  </>
                )}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">Sandbox Execution</span>
              <span className="flex items-center gap-1">
                {(verification as any).sandbox_passed ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span className="text-green-700 font-medium">PASSED</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-red-500" />
                    <span className="text-red-700 font-medium">FAILED</span>
                  </>
                )}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">Judge Score</span>
              <span className="font-semibold text-slate-900">
                {(((verification as any).judge_score ?? 0) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">CoVE Verified</span>
              <span className="font-semibold text-slate-900">
                {((verification as any).cove_verified_percent ?? 0).toFixed(0)}%
              </span>
            </div>
          </div>
        </motion.div>

        {/* Timing Breakdown */}
        {timingData.length > 0 && (
          <motion.div
            className="p-4 rounded-lg bg-white border border-slate-200"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
          >
            <p className="text-xs font-semibold text-slate-700 mb-3">TIMING BREAKDOWN (ms)</p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={timingData} margin={{ top: 5, right: 5, left: 0, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11 }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value: any) => `${(value || 0).toFixed(1)}ms`} />
                <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p className="text-xs text-slate-600 mt-2">
              Total: {(((totalTime as number) || 0) / 1000).toFixed(2)}s
            </p>
          </motion.div>
        )}

        {/* Alerts */}
        {metrics.alerts && metrics.alerts.length > 0 && (
          <motion.div
            className="p-4 rounded-lg bg-amber-50 border border-amber-200"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.3 }}
          >
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-xs font-semibold text-amber-900 mb-1">ALERTS</p>
                <ul className="text-xs text-amber-800 space-y-1">
                  {metrics.alerts.map((alert, idx) => (
                    <li key={idx}>• {alert}</li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>
        )}

        {/* Policy Decision Badge */}
        <motion.div
          className={`p-3 rounded-lg text-center border-2 ${
            policyDecision === 'accept'
              ? 'bg-green-50 border-green-300'
              : policyDecision === 'reject'
                ? 'bg-red-50 border-red-300'
                : policyDecision === 'repair'
                  ? 'bg-amber-50 border-amber-300'
                  : 'bg-blue-50 border-blue-300'
          }`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.4 }}
        >
          <p className="text-xs font-semibold text-slate-700 mb-1">FINAL DECISION</p>
          <p
            className={`text-lg font-bold ${
              policyDecision === 'accept'
                ? 'text-green-700'
                : policyDecision === 'reject'
                  ? 'text-red-700'
                  : policyDecision === 'repair'
                    ? 'text-amber-700'
                    : 'text-blue-700'
            }`}
          >
            {policyDecision.toUpperCase()}
          </p>
        </motion.div>
      </div>
    </motion.div>
  );
}
