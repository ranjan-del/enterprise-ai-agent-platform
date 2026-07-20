// Conversations + chat. Wraps the conversation/message endpoints.
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ChatResponse, Conversation, Message } from '../models';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private api = inject(ApiService);

  listConversations(): Observable<Conversation[]> {
    return this.api.get<Conversation[]>('/conversations');
  }

  createConversation(agentId?: number | null): Observable<Conversation> {
    return this.api.post<Conversation>('/conversations', { agent_id: agentId ?? null });
  }

  listMessages(conversationId: number): Observable<Message[]> {
    return this.api.get<Message[]>(`/conversations/${conversationId}/messages`);
  }

  sendMessage(conversationId: number, content: string): Observable<ChatResponse> {
    return this.api.post<ChatResponse>(`/conversations/${conversationId}/messages`, { content });
  }
}
