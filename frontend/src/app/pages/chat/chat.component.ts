// Chat workspace: conversation list, message thread, and composer.
import { AfterViewChecked, Component, ElementRef, ViewChild, inject, signal } from '@angular/core';
import { NgClass, NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat.service';
import { Conversation, Message } from '../../models';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [NgFor, NgIf, NgClass, FormsModule],
  template: `
    <div class="chat-layout">
      <aside class="conv-list">
        <button class="btn sm block" (click)="newConversation()">＋ New conversation</button>
        <div class="convs">
          <button
            *ngFor="let c of conversations()"
            class="conv"
            [ngClass]="{ active: c.id === activeId() }"
            (click)="select(c.id)"
          >
            <span class="conv-title">{{ c.title }}</span>
          </button>
          <p class="muted empty" *ngIf="conversations().length === 0">No conversations yet.</p>
        </div>
      </aside>

      <section class="thread-wrap">
        <div class="thread" #thread>
          <div class="empty-state" *ngIf="activeId() === null">
            <h2>Start a conversation</h2>
            <p>Try “calculate 12 * 8”, “what is the time”, or “note: buy milk”.</p>
          </div>
          <div
            *ngFor="let m of messages()"
            class="msg"
            [ngClass]="{ user: m.role === 'user', assistant: m.role === 'assistant' }"
          >
            <div class="avatar" aria-hidden="true">{{ m.role === 'user' ? 'U' : '◆' }}</div>
            <div class="bubble">{{ m.content }}</div>
          </div>
          <div class="msg assistant" *ngIf="sending()">
            <div class="avatar" aria-hidden="true">◆</div>
            <div class="bubble typing"><span></span><span></span><span></span></div>
          </div>
        </div>

        <form class="composer" (ngSubmit)="send()">
          <input
            class="input"
            [(ngModel)]="draft"
            name="draft"
            placeholder="Message the assistant…"
            autocomplete="off"
            [disabled]="sending()"
            aria-label="Message"
          />
          <button class="btn" type="submit" [disabled]="sending() || !draft.trim()">Send</button>
        </form>
      </section>
    </div>
  `,
  styles: [
    `
      .chat-layout { display: grid; grid-template-columns: 240px 1fr; gap: 1rem; height: calc(100vh - 140px); }
      .conv-list { display: flex; flex-direction: column; gap: 0.75rem; min-height: 0; }
      .convs { display: flex; flex-direction: column; gap: 0.25rem; overflow-y: auto; }
      .conv { text-align: left; background: transparent; border: 1px solid transparent; color: var(--text-dim);
        padding: 0.55rem 0.65rem; border-radius: var(--radius-sm); cursor: pointer; font: inherit; }
      .conv:hover { background: var(--bg-elev-2); color: var(--text); }
      .conv.active { background: var(--brand-soft); color: var(--brand); }
      .conv-title { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .empty { padding: 0.5rem; }

      .thread-wrap { display: flex; flex-direction: column; border: 1px solid var(--border); border-radius: var(--radius);
        background: var(--bg-elev); min-height: 0; }
      .thread { flex: 1; overflow-y: auto; padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; }
      .empty-state { margin: auto; text-align: center; color: var(--text-dim); }

      .msg { display: flex; gap: 0.7rem; max-width: 80%; }
      .msg.user { align-self: flex-end; flex-direction: row-reverse; }
      .avatar { flex-shrink: 0; width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
        font-size: 0.8rem; font-weight: 700; background: var(--bg-elev-2); color: var(--brand); }
      .msg.user .avatar { background: var(--brand-600); color: #fff; }
      .bubble { padding: 0.65rem 0.9rem; border-radius: 12px; background: var(--surface); white-space: pre-wrap;
        line-height: 1.5; border: 1px solid var(--border); }
      .msg.user .bubble { background: var(--brand-600); color: #fff; border-color: transparent; }

      .typing { display: inline-flex; gap: 4px; }
      .typing span { width: 6px; height: 6px; border-radius: 50%; background: var(--text-faint); animation: blink 1.2s infinite; }
      .typing span:nth-child(2) { animation-delay: 0.2s; }
      .typing span:nth-child(3) { animation-delay: 0.4s; }
      @keyframes blink { 0%, 60%, 100% { opacity: 0.25; } 30% { opacity: 1; } }

      .composer { display: flex; gap: 0.6rem; padding: 0.9rem; border-top: 1px solid var(--border); }

      @media (max-width: 820px) {
        .chat-layout { grid-template-columns: 1fr; height: auto; }
        .convs { max-height: 140px; }
        .thread { min-height: 50vh; }
      }
    `,
  ],
})
export class ChatComponent implements AfterViewChecked {
  private chat = inject(ChatService);
  @ViewChild('thread') threadEl?: ElementRef<HTMLDivElement>;

  conversations = signal<Conversation[]>([]);
  messages = signal<Message[]>([]);
  activeId = signal<number | null>(null);
  sending = signal(false);
  draft = '';
  private shouldScroll = false;

  constructor() {
    this.loadConversations();
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll && this.threadEl) {
      this.threadEl.nativeElement.scrollTop = this.threadEl.nativeElement.scrollHeight;
      this.shouldScroll = false;
    }
  }

  private loadConversations(): void {
    this.chat.listConversations().subscribe((cs) => {
      this.conversations.set(cs);
      if (cs.length && this.activeId() === null) {
        this.select(cs[0].id);
      }
    });
  }

  select(id: number): void {
    this.activeId.set(id);
    this.chat.listMessages(id).subscribe((ms) => {
      this.messages.set(ms);
      this.shouldScroll = true;
    });
  }

  newConversation(): void {
    this.chat.createConversation().subscribe((c) => {
      this.conversations.update((cs) => [c, ...cs]);
      this.activeId.set(c.id);
      this.messages.set([]);
    });
  }

  send(): void {
    const text = this.draft.trim();
    if (!text || this.sending()) return;

    const ensure = this.activeId() === null
      ? this.chat.createConversation()
      : null;

    if (ensure) {
      ensure.subscribe((c) => {
        this.conversations.update((cs) => [c, ...cs]);
        this.activeId.set(c.id);
        this.dispatch(c.id, text);
      });
    } else {
      this.dispatch(this.activeId()!, text);
    }
    this.draft = '';
  }

  private dispatch(conversationId: number, text: string): void {
    this.messages.update((ms) => [
      ...ms,
      { id: Date.now(), role: 'user', content: text, created_at: '' },
    ]);
    this.shouldScroll = true;
    this.sending.set(true);
    this.chat.sendMessage(conversationId, text).subscribe({
      next: (res) => {
        this.sending.set(false);
        this.messages.update((ms) => [...ms, res.assistant_message]);
        this.shouldScroll = true;
        // Refresh titles (a new conversation gets auto-titled server-side).
        this.chat.listConversations().subscribe((cs) => this.conversations.set(cs));
      },
      error: () => {
        this.sending.set(false);
        this.messages.update((ms) => [
          ...ms,
          { id: Date.now(), role: 'assistant', content: 'Sorry, something went wrong sending that message.', created_at: '' },
        ]);
        this.shouldScroll = true;
      },
    });
  }
}
