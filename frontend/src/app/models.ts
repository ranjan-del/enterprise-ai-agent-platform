// Shared API types mirroring the backend Pydantic schemas.

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
  org_id: number;
}

export interface Tool {
  name: string;
  description: string;
  parameters: Record<string, string>;
  examples: string[];
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

export interface ChatResponse {
  conversation_id: number;
  user_message: Message;
  assistant_message: Message;
  tools_used: string[];
  steps: { node: string; detail: string }[];
}

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
