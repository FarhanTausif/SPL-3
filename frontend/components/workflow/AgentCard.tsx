'use client';

import { motion } from 'framer-motion';
import { CheckCircle2, Clock, Zap } from 'lucide-react';
import { ReactNode } from 'react';

export type AgentStatus = 'idle' | 'running' | 'complete' | 'error';

interface AgentCardProps {
  name: string;
  role: string;
  status: AgentStatus;
  progress?: number; // 0-100
  duration?: number; // milliseconds
  icon?: ReactNode;
  onClick?: () => void;
  expandable?: boolean;
}

const statusConfig = {
  idle: {
    bg: 'bg-slate-100',
    border: 'border-slate-300',
    textColor: 'text-slate-700',
    dotColor: 'bg-slate-400',
    label: 'Pending',
  },
  running: {
    bg: 'bg-blue-50',
    border: 'border-blue-300',
    textColor: 'text-blue-700',
    dotColor: 'bg-blue-500',
    label: 'Running',
  },
  complete: {
    bg: 'bg-green-50',
    border: 'border-green-300',
    textColor: 'text-green-700',
    dotColor: 'bg-green-500',
    label: 'Complete',
  },
  error: {
    bg: 'bg-red-50',
    border: 'border-red-300',
    textColor: 'text-red-700',
    dotColor: 'bg-red-500',
    label: 'Error',
  },
};

export function AgentCard({
  name,
  role,
  status,
  progress = 0,
  duration,
  icon,
  onClick,
  expandable = false,
}: AgentCardProps) {
  const config = statusConfig[status];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && onClick) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <motion.div
      className={`
        relative rounded-lg border-2 p-4 transition-all
        ${config.bg} ${config.border}
        ${status === 'running' ? 'ring-2 ring-blue-300 ring-opacity-50' : ''}
        ${expandable ? 'cursor-pointer hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2' : ''}
      `}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={expandable ? 'button' : undefined}
      tabIndex={expandable ? 0 : undefined}
      aria-label={`${name} agent - ${role} - Status: ${config.label}`}
      aria-live="polite"
      aria-busy={status === 'running'}
      animate={{
        scale: status === 'running' ? 1.02 : 1,
        boxShadow:
          status === 'running'
            ? '0 10px 30px rgba(59, 130, 246, 0.3)'
            : '0 4px 6px rgba(0, 0, 0, 0.1)',
      }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3 flex-1">
          {/* Status Dot */}
          <div className="pt-1">
            {status === 'running' ? (
              <motion.div
                className={`w-3 h-3 rounded-full ${config.dotColor}`}
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
            ) : status === 'complete' ? (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200 }}
              >
                <CheckCircle2 className={`w-5 h-5 ${config.textColor}`} />
              </motion.div>
            ) : (
              <div className={`w-3 h-3 rounded-full ${config.dotColor}`} />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className={`font-semibold text-sm md:text-base ${config.textColor}`}>
                {name}
              </h3>
              {icon && <div className="text-lg">{icon}</div>}
            </div>
            <p className={`text-xs md:text-sm opacity-75 ${config.textColor}`}>
              {role}
            </p>
          </div>
        </div>

        {/* Status Badge */}
        <motion.div
          className={`px-2 py-1 rounded-md text-xs font-medium whitespace-nowrap ml-2 ${config.bg} ${config.textColor}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          {config.label}
        </motion.div>
      </div>

      {/* Progress Bar */}
      {status !== 'idle' && progress > 0 && (
        <motion.div className="mt-3 w-full bg-white/50 rounded-full h-2 overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${statusConfig[status].dotColor}`}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </motion.div>
      )}

      {/* Metadata */}
      {duration && (
        <motion.div
          className={`mt-2 flex items-center gap-1 text-xs ${config.textColor}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <Clock className="w-3 h-3" />
          <span>{(duration / 1000).toFixed(2)}s</span>
        </motion.div>
      )}

      {/* Expandable Indicator */}
      {expandable && (
        <div className="absolute top-2 right-2">
          <Zap className={`w-4 h-4 ${config.textColor} opacity-50`} />
        </div>
      )}
    </motion.div>
  );
}
