// Shared API types mirroring the backend Pydantic schemas.
// Keep these in step with backend/app/schemas/*.py: they are the contract the
// pages rely on, and TypeScript's strict mode is what catches drift early.

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Org {
  id: number;
  name: string;
  slug: string;
  plan: string;
}

export interface User {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  org_id: number;
}

export interface Me {
  user: User;
  org: Org;
}

export interface Agent {
  id: number;
  name: string;
  description: string;
  system_prompt: string;
  tools: string[];
  // Peer agents this one may hand a tool call to (multi-agent collaboration).
  teammates: number[];
  // When true every tool call pauses for a human decision on the Logs page.
  requires_approval: boolean;
  org_id: number;
}

export interface Tool {
  name: string;
  description: string;
  parameters: Record<string, string>;
  examples: string[];
  // Network tools are off unless the backend sets ALLOW_NETWORK_TOOLS.
  requires_network: boolean;
}

export interface Conversation {
  id: number;
  title: string;
  agent_id: number | null;
  user_id: number;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

export interface AgentStep {
  node: string;
  detail: string;
}

export interface ChatResponse {
  conversation_id: number;
  user_message: Message;
  assistant_message: Message;
  tools_used: string[];
  steps: AgentStep[];
  status: string;
}

/** One Server-Sent Event from the streaming chat endpoint. */
export type StreamEvent =
  | { event: 'step'; node: string; detail: string }
  | {
      event: 'result';
      conversation_id: number;
      message_id: number;
      execution_id: number;
      status: string;
      tools_used: string[];
      reply: string;
    };

export interface UsageMetrics {
  org_id: number;
  users: number;
  agents: number;
  conversations: number;
  messages: number;
  executions: number;
  tokens_used: number;
}

export interface ExecutionAnalytics {
  total_executions: number;
  completed: number;
  failed: number;
  awaiting_approval: number;
  rejected: number;
  tokens_used: number;
  tool_usage: Record<string, number>;
}

export interface Execution {
  id: number;
  agent_id: number | null;
  conversation_id: number | null;
  status: string;
  tokens_used: number;
  started_at: string;
  finished_at: string;
}

/** An execution plus its full trace and, if paused, the tool awaiting approval. */
export interface ExecutionDetail extends Execution {
  steps: AgentStep[];
  pending_action: { tool: string; params: Record<string, unknown>; message: string } | null;
}

export interface Fact {
  id: number;
  fact: string;
  created_at: string;
}

export interface RecallHit {
  id: number;
  kind: string;
  text: string;
  score: number;
}

export interface RecallResponse {
  query: string;
  hits: RecallHit[];
}

export interface MemoryOverview {
  facts: number;
  documents: number;
  messages: number;
}

export interface SessionWindow {
  conversation_id: number;
  turns: { role: string; content: string }[];
}
