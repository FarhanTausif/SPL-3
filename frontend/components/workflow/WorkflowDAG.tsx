'use client';

import { useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { motion } from 'framer-motion';
import { AgentCard, AgentStatus } from './AgentCard';
import {
  Lightbulb,
  Code2,
  CheckSquare,
  AlertCircle,
  Zap,
  Brain,
  Shield,
  Package,
  Wrench,
} from 'lucide-react';

export interface StageAgent {
  name: string;
  role: string;
  status: AgentStatus;
  progress?: number;
  duration?: number;
  stage: string;
}

interface WorkflowDAGProps {
  agents: StageAgent[];
  policyDecision?: 'accept' | 'warn' | 'repair' | 'reject';
  isRepairLoopActive?: boolean;
}

const agentIcons = {
  Clarification: <Lightbulb className="w-5 h-5" />,
  Generation: <Code2 className="w-5 h-5" />,
  'Claim Extraction': <CheckSquare className="w-5 h-5" />,
  'Static Analysis': <AlertCircle className="w-5 h-5" />,
  Sandbox: <Zap className="w-5 h-5" />,
  Judge: <Brain className="w-5 h-5" />,
  CoVE: <Shield className="w-5 h-5" />,
  Policy: <Package className="w-5 h-5" />,
  Repair: <Wrench className="w-5 h-5" />,
};

export function WorkflowDAG({
  agents,
  policyDecision = 'accept',
  isRepairLoopActive = false,
}: WorkflowDAGProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node[]>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge[]>([]);

  // Build DAG from agents
  useEffect(() => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];
    const stagePositions: Record<string, number> = {};

    // Group agents by stage
    const stages = [
      'Input',
      'Clarification',
      'Generation',
      'VerificationParallel',
      'Policy',
      'Repair',
      'Results',
    ];

    let yOffset = 0;

    // Input node
    newNodes.push({
      id: 'input',
      data: { label: 'User Input' },
      position: { x: 50, y: yOffset },
      style: {
        background: '#f0f9ff',
        border: '2px solid #0284c7',
        borderRadius: '8px',
        padding: '10px 15px',
        fontSize: '12px',
        fontWeight: 'bold',
      },
    });

    // Sequential stages
    const sequentialStages = [
      { id: 'clarification', agents: agents.filter((a) => a.stage === 'Clarification') },
      { id: 'generation', agents: agents.filter((a) => a.stage === 'Generation') },
      {
        id: 'verification',
        agents: agents.filter((a) =>
          ['Claim Extraction', 'Static Analysis', 'Sandbox', 'Judge', 'CoVE'].includes(
            a.stage
          )
        ),
      },
      { id: 'policy', agents: agents.filter((a) => a.stage === 'Policy') },
    ];

    let currentY = 120;

    for (const stage of sequentialStages) {
      if (stage.agents.length === 0) continue;

      const stageId = stage.id;
      const startX = 50;

      if (stage.agents.length === 1) {
        // Single agent
        const agent = stage.agents[0];
        newNodes.push({
          id: `${stageId}-${0}`,
          data: {
            label: (
              <AgentCard
                name={agent.name}
                role={agent.role}
                status={agent.status}
                progress={agent.progress}
                duration={agent.duration}
                icon={
                  agentIcons[agent.name as keyof typeof agentIcons] || <Zap />
                }
              />
            ),
          },
          position: { x: startX, y: currentY },
          style: { background: 'transparent', border: 'none' },
        });
      } else {
        // Parallel agents
        const agentWidth = 200;
        const spacing = 20;
        const totalWidth = stage.agents.length * (agentWidth + spacing);
        const startXParallel = startX - totalWidth / 2 + agentWidth / 2;

        stage.agents.forEach((agent, idx) => {
          newNodes.push({
            id: `${stageId}-${idx}`,
            data: {
              label: (
                <AgentCard
                  name={agent.name}
                  role={agent.role}
                  status={agent.status}
                  progress={agent.progress}
                  duration={agent.duration}
                  icon={
                    agentIcons[agent.name as keyof typeof agentIcons] || <Zap />
                  }
                />
              ),
            },
            position: {
              x: startXParallel + idx * (agentWidth + spacing),
              y: currentY,
            },
            style: { background: 'transparent', border: 'none' },
          });
        });
      }

      currentY += 200;
    }

    // Policy decision node
    const decisionColor =
      policyDecision === 'accept'
        ? '#10b981'
        : policyDecision === 'reject'
          ? '#ef4444'
          : policyDecision === 'repair'
            ? '#f59e0b'
            : '#6366f1';

    newNodes.push({
      id: 'decision',
      data: { label: `Decision: ${policyDecision.toUpperCase()}` },
      position: { x: 50, y: currentY },
      style: {
        background: decisionColor,
        color: 'white',
        border: `2px solid ${decisionColor}`,
        borderRadius: '8px',
        padding: '12px 20px',
        fontSize: '13px',
        fontWeight: 'bold',
      },
    });

    // Repair loop (if active)
    if (isRepairLoopActive) {
      const repairY = currentY + 150;
      newNodes.push({
        id: 'repair',
        data: {
          label: (
            <AgentCard
              name="Repair Agent"
              role="Fixer"
              status="running"
              icon={<Wrench className="w-5 h-5" />}
            />
          ),
        },
        position: { x: 50, y: repairY },
        style: { background: 'transparent', border: 'none' },
      });

      newEdges.push({
        id: 'decision-to-repair',
        source: 'decision',
        target: 'repair',
        animated: true,
        style: { stroke: '#f59e0b', strokeWidth: 2 },
      });

      currentY = repairY + 150;
    }

    // Results node
    newNodes.push({
      id: 'results',
      data: { label: 'Return Results' },
      position: { x: 50, y: currentY + 100 },
      style: {
        background: '#f0fdf4',
        border: '2px solid #16a34a',
        borderRadius: '8px',
        padding: '10px 15px',
        fontSize: '12px',
        fontWeight: 'bold',
      },
    });

    // Add edges for sequential flow
    newEdges.push(
      { id: 'input-to-clarification', source: 'input', target: 'clarification-0' },
      { id: 'clarification-to-generation', source: 'clarification-0', target: 'generation-0' },
      { id: 'generation-to-verification', source: 'generation-0', target: 'verification-0' },
      { id: 'verification-to-policy', source: 'verification-0', target: 'policy-0' },
      { id: 'policy-to-decision', source: 'policy-0', target: 'decision' },
      {
        id: 'decision-to-results',
        source: 'decision',
        target: 'results',
        animated: policyDecision === 'accept',
      }
    );

    setNodes(newNodes);
    setEdges(newEdges);
  }, [agents, policyDecision, isRepairLoopActive, setNodes, setEdges]);

  return (
    <motion.div
      className="w-full h-full bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg overflow-hidden border border-slate-200"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      role="region"
      aria-label="Agent workflow execution pipeline"
    >
      <ReactFlow 
        nodes={nodes} 
        edges={edges} 
        onNodesChange={onNodesChange} 
        onEdgesChange={onEdgesChange}
        aria-label="Workflow DAG visualization showing agent execution flow"
      >
        <Background color="#a1a5ab" gap={16} />
        <Controls />
      </ReactFlow>
    </motion.div>
  );
}
