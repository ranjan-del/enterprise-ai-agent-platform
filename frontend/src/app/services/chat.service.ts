// Conversations + chat. Wraps the conversation/message endpoints, including
// the Server-Sent Events variant used to show the agent thinking live.
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { ChatResponse, Conversation, Message, StreamEvent } from '../models';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private api = inject(ApiService);
  private auth = inject(AuthService);

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

  /**
   * Stream one turn as Server-Sent Events.
   *
   * HttpClient cannot expose a response body incrementally, so this uses fetch
   * with a ReadableStream reader instead. The auth header is attached by hand
   * for the same reason: the HTTP interceptor never sees this request.
   */
  streamMessage(conversationId: number, content: string): Observable<StreamEvent> {
    const url = `${environment.apiBase}/conversations/${conversationId}/messages/stream`;
    const token = this.auth.getAccessToken();

    return new Observable<StreamEvent>((subscriber) => {
      const controller = new AbortController();

      fetch(url, {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content }),
      })
        .then(async (response) => {
          if (!response.ok || !response.body) {
            throw new Error(`stream failed with HTTP ${response.status}`);
          }
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          // SSE frames are separated by a blank line, and a network chunk can
          // split one in half, so the tail is carried into the next read.
          let buffer = '';
          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const frames = buffer.split('\n\n');
            buffer = frames.pop() ?? '';
            for (const frame of frames) {
              for (const line of frame.split('\n')) {
                if (line.startsWith('data: ')) {
                  subscriber.next(JSON.parse(line.slice(6)) as StreamEvent);
                }
              }
            }
          }
          subscriber.complete();
        })
        .catch((err) => {
          if (!controller.signal.aborted) subscriber.error(err);
        });

      // Unsubscribing (leaving the page mid-turn) aborts the request. The
      // backend only persists a turn after its final node, so nothing is
      // half-written when that happens.
      return () => controller.abort();
    });
  }
}
