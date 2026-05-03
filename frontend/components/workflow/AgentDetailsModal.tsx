/**
 * Agent Details Modal / Drawer
 * Displays comprehensive agent execution information
 */

'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock, Code, AlertCircle, CheckCircle } from 'lucide-react';

export interface AgentExecutionDetail {
  agentName: string;
  role: string;
  taskDescription: string;
  fullTaskPrompt: string;
  mcpTools: string[];
  executionTimeline: Array<{
    timestamp: number;
    step: string;
    duration: number;
  }>;
  inputPayload: Record<string, any>;
  outputPayload: Record<string, any>;
  logs: string[];
  error?: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  durationMs: number;
}

interface AgentDetailsModalProps {
  isOpen: boolean;
  agent: AgentExecutionDetail | null;
  onClose: () => void;
}

export function AgentDetailsModal({ isOpen, agent, onClose }: AgentDetailsModalProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('overview');

  if (!agent) return null;

  const totalDuration = agent.durationMs;
  const statusColor = {
    idle: 'bg-gray-100 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
  }[agent.status];

  const statusIcon = {
    idle: null,
    running: <motion.div className="animate-spin">⏳</motion.div>,
    completed: <CheckCircle className="w-5 h-5" />,
    error: <AlertCircle className="w-5 h-5" />,
  }[agent.status];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-white z-50 shadow-xl overflow-y-auto"
          >
            {/* Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-2 rounded-lg ${statusColor}`}>{statusIcon}</div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{agent.agentName}</h2>
                  <p className="text-sm text-gray-500">{agent.role}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Close modal"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Quick Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-xs font-semibold text-blue-600">Status</div>
                  <div className="text-lg font-bold text-blue-900 capitalize">{agent.status}</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-xs font-semibold text-purple-600">Duration</div>
                  <div className="text-lg font-bold text-purple-900">{totalDuration}ms</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-xs font-semibold text-green-600">Tools</div>
                  <div className="text-lg font-bold text-green-900">{agent.mcpTools.length}</div>
                </div>
              </div>

              {/* Expandable Sections */}

              {/* Overview */}
              <ExpandableSection
                title="Overview"
                isExpanded={expandedSection === 'overview'}
                onClick={() =>
                  setExpandedSection(expandedSection === 'overview' ? null : 'overview')
                }
              >
                <div className="space-y-3 text-sm">
                  <div>
                    <p className="font-semibold text-gray-700">Task Description</p>
                    <p className="text-gray-600 mt-1">{agent.taskDescription}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-700">Available MCP Tools</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {agent.mcpTools.length > 0 ? (
                        agent.mcpTools.map((tool) => (
                          <span key={tool} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                            {tool}
                          </span>
                        ))
                      ) : (
                        <span className="text-gray-500">No MCP tools available</span>
                      )}
                    </div>
                  </div>
                </div>
              </ExpandableSection>

              {/* Task Prompt */}
              <ExpandableSection
                title="Full Task Prompt"
                isExpanded={expandedSection === 'prompt'}
                onClick={() =>
                  setExpandedSection(expandedSection === 'prompt' ? null : 'prompt')
                }
              >
                <pre className="bg-gray-100 p-4 rounded text-xs overflow-x-auto text-gray-700 max-h-64">
                  {agent.fullTaskPrompt}
                </pre>
              </ExpandableSection>

              {/* Execution Timeline */}
              <ExpandableSection
                title={`Execution Timeline (${agent.executionTimeline.length} steps)`}
                isExpanded={expandedSection === 'timeline'}
                onClick={() =>
                  setExpandedSection(expandedSection === 'timeline' ? null : 'timeline')
                }
              >
                <div className="space-y-3">
                  {agent.executionTimeline.map((step, idx) => (
                    <div key={idx} className="flex gap-4 text-sm">
                      <div className="flex flex-col items-center">
                        <div className="w-2 h-2 bg-blue-500 rounded-full" />
                        {idx < agent.executionTimeline.length - 1 && (
                          <div className="w-0.5 h-12 bg-gray-200 mt-1" />
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <p className="font-semibold text-gray-900">{step.step}</p>
                        <p className="text-gray-500 text-xs">
                          {new Date(step.timestamp).toLocaleTimeString()} • {step.duration}ms
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </ExpandableSection>

              {/* Input Payload */}
              <ExpandableSection
                title="Input Payload"
                isExpanded={expandedSection === 'input'}
                onClick={() =>
                  setExpandedSection(expandedSection === 'input' ? null : 'input')
                }
              >
                <pre className="bg-gray-100 p-4 rounded text-xs overflow-x-auto max-h-64">
                  {JSON.stringify(agent.inputPayload, null, 2)}
                </pre>
              </ExpandableSection>

              {/* Output Payload */}
              <ExpandableSection
                title="Output Payload"
                isExpanded={expandedSection === 'output'}
                onClick={() =>
                  setExpandedSection(expandedSection === 'output' ? null : 'output')
                }
              >
                <pre className="bg-gray-100 p-4 rounded text-xs overflow-x-auto max-h-64">
                  {JSON.stringify(agent.outputPayload, null, 2)}
                </pre>
              </ExpandableSection>

              {/* Logs */}
              <ExpandableSection
                title={`Logs (${agent.logs.length} entries)`}
                isExpanded={expandedSection === 'logs'}
                onClick={() =>
                  setExpandedSection(expandedSection === 'logs' ? null : 'logs')
                }
              >
                <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-xs space-y-1 max-h-64 overflow-y-auto">
                  {agent.logs.length > 0 ? (
                    agent.logs.map((log, idx) => (
                      <div key={idx} className="text-gray-400">
                        &gt; {log}
                      </div>
                    ))
                  ) : (
                    <div className="text-gray-600">No logs available</div>
                  )}
                </div>
              </ExpandableSection>

              {/* Error Details (if any) */}
              {agent.error && (
                <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600" />
                    <h3 className="font-semibold text-red-900">Error Details</h3>
                  </div>
                  <pre className="mt-2 text-xs text-red-800 overflow-x-auto bg-red-100 p-2 rounded">
                    {agent.error}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/**
 * Reusable expandable section component
 */
function ExpandableSection({
  title,
  isExpanded,
  onClick,
  children,
}: {
  title: string;
  isExpanded: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={onClick}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors text-left"
      >
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          ▼
        </motion.div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-gray-200 bg-gray-50 overflow-hidden"
          >
            <div className="p-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
