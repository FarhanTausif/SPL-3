/**
 * Lazy-loaded components for performance optimization
 * Reduces initial page load by code-splitting heavy components
 */

import React from 'react'
import dynamic from 'next/dynamic'
import { ComponentType } from 'react'

// Create loading placeholder component
const LoadingPlaceholder = () => (
  <div className="w-full h-64 bg-gradient-to-r from-slate-200 to-slate-100 animate-pulse rounded-lg" />
)

export const LazyWorkflowDAG = dynamic(
  () => import('@/components/workflow/WorkflowDAG').then(mod => mod.WorkflowDAG),
  {
    loading: LoadingPlaceholder,
    ssr: false, // Workflow visualization is client-only
  }
) as ComponentType<any>

export const LazyEvidencePanel = dynamic(
  () => import('@/components/workflow/EvidencePanel').then(mod => mod.EvidencePanel),
  {
    loading: LoadingPlaceholder,
    ssr: false,
  }
) as ComponentType<any>

export const LazyMetricsPanel = dynamic(
  () => import('@/components/workflow/MetricsPanel').then(mod => mod.MetricsPanel),
  {
    loading: LoadingPlaceholder,
    ssr: false,
  }
) as ComponentType<any>

export const LazyResultsDisplay = dynamic(
  () => import('@/components/ResultsDisplay').then(mod => mod.ResultsDisplay),
  {
    loading: LoadingPlaceholder,
    ssr: true,
  }
) as ComponentType<any>
