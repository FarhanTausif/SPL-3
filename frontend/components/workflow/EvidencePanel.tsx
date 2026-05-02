'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Copy, Check } from 'lucide-react';
import { useState as useStateHook } from 'react';

export interface EvidenceItem {
  kind:
    | 'claim_extraction'
    | 'static_analysis'
    | 'sandbox_execution'
    | 'judge_verdict'
    | 'cove_verification'
    | 'policy_decision'
    | 'repair_attempt';
  summary: string;
  count?: number;
  status: 'pending' | 'in_progress' | 'success' | 'warning' | 'error';
  payload: Record<string, unknown>;
  timestamp?: string;
}

interface EvidencePanelProps {
  evidence: EvidenceItem[];
  loading?: boolean;
}

const evidenceConfig = {
  claim_extraction: {
    label: 'Claim Extraction',
    icon: '📋',
    color: 'blue',
  },
  static_analysis: {
    label: 'Static Analysis',
    icon: '🔍',
    color: 'purple',
  },
  sandbox_execution: {
    label: 'Sandbox Execution',
    icon: '🏃',
    color: 'green',
  },
  judge_verdict: {
    label: 'Judge Verdict',
    icon: '⚖️',
    color: 'amber',
  },
  cove_verification: {
    label: 'CoVE Verification',
    icon: '✔️',
    color: 'cyan',
  },
  policy_decision: {
    label: 'Policy Decision',
    icon: '📋',
    color: 'indigo',
  },
  repair_attempt: {
    label: 'Repair Attempt',
    icon: '🔧',
    color: 'orange',
  },
};

const statusColors = {
  pending: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  warning: 'bg-amber-100 text-amber-700',
  error: 'bg-red-100 text-red-700',
};

function EvidenceItemCard({ item }: { item: EvidenceItem }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const config = evidenceConfig[item.kind];

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(item.payload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      className="border border-slate-200 rounded-lg overflow-hidden bg-white hover:shadow-md transition-shadow"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      role="region"
      aria-label={`${config.label} evidence`}
    >
      {/* Header */}
      <motion.button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls={`evidence-detail-${item.kind}`}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset"
        whileHover={{ backgroundColor: 'rgba(15, 23, 42, 0.05)' }}
      >
        <div className="flex items-center gap-3 flex-1 text-left">
          <span className="text-xl">{config.icon}</span>
          <div>
            <h4 className="font-semibold text-sm text-slate-900">{config.label}</h4>
            <p className="text-xs text-slate-600 line-clamp-1">{item.summary}</p>
          </div>
          {item.count && (
            <span className="ml-auto mr-2 px-2 py-1 bg-slate-100 rounded text-xs font-medium text-slate-700">
              {item.count} items
            </span>
          )}
        </div>

        {/* Status Badge */}
        <motion.span
          className={`px-2 py-1 rounded text-xs font-medium ${statusColors[item.status]} ml-2`}
        >
          {item.status === 'in_progress' ? '⏳' : item.status === 'success' ? '✅' : item.status === 'error' ? '❌' : '⭕'}
        </motion.span>

        {/* Expand Arrow */}
        <motion.div
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-5 h-5 text-slate-500" />
        </motion.div>
      </motion.button>

      {/* Expandable Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-slate-200 bg-slate-50 overflow-hidden"
            id={`evidence-detail-${item.kind}`}
          >
            <div className="p-4 space-y-3">
              {/* Payload Display */}
              <div className="bg-white rounded border border-slate-200 p-3 font-mono text-xs overflow-auto max-h-64">
                <pre className="text-slate-700">
                  {JSON.stringify(item.payload, null, 2)}
                </pre>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={handleCopy}
                  aria-label={copied ? 'Evidence JSON copied to clipboard' : 'Copy evidence JSON to clipboard'}
                  className="flex items-center gap-2 px-3 py-2 bg-slate-200 hover:bg-slate-300 rounded text-xs font-medium text-slate-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      Copy JSON
                    </>
                  )}
                </button>
              </div>

              {/* Timestamp */}
              {item.timestamp && (
                <p className="text-xs text-slate-600">
                  Recorded: {new Date(item.timestamp).toLocaleString()}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export function EvidencePanel({ evidence, loading = false }: EvidencePanelProps) {
  return (
    <motion.div
      className="flex flex-col h-full bg-white rounded-lg border border-slate-200"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      role="region"
      aria-label="Evidence collection results"
      aria-live="polite"
      aria-busy={loading}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-transparent">
        <h3 className="font-semibold text-sm text-slate-900">
          📊 Evidence Collected (<span aria-live="polite">{evidence.length}</span>)
        </h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center h-32" role="status" aria-label="Loading evidence">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity }}
              className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"
            />
          </div>
        ) : evidence.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-slate-500" role="status">
            <p className="text-sm">No evidence collected yet...</p>
          </div>
        ) : (
          <AnimatePresence>
            {evidence.map((item, idx) => (
              <EvidenceItemCard key={`${item.kind}-${idx}`} item={item} />
            ))}
          </AnimatePresence>
        )}
      </div>
    </motion.div>
  );
}
