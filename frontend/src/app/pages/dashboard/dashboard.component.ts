// Dashboard: workspace overview with usage stat tiles and quick actions.
import { Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { UsageMetrics } from '../../models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NgFor, NgIf, RouterLink],
  template: `
    <header class="page-head">
      <h1>Welcome{{ name() ? ', ' + name() : '' }}</h1>
      <p>Here's what's happening in your workspace.</p>
    </header>

    <section class="stats" *ngIf="usage() as u">
      <div class="card stat" *ngFor="let s of tiles(u)">
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">{{ s.value }}</div>
      </div>
    </section>
    <p class="muted" *ngIf="!usage() && !error()">Loading metrics…</p>
    <p class="error-text" *ngIf="error()">{{ error() }}</p>

    <section class="actions">
      <a class="card action" routerLink="/chat">
        <h3>✦ Start chatting</h3>
        <p>Open a conversation with your workspace assistant.</p>
      </a>
      <a class="card action" routerLink="/agents">
        <h3>◈ Configure agents</h3>
        <p>Create agents and choose which tools they can use.</p>
      </a>
      <a class="card action" routerLink="/analytics">
        <h3>◔ View analytics</h3>
        <p>Track executions, tokens, and tool usage.</p>
      </a>
    </section>
  `,
  styles: [
    `
      .page-head { margin-bottom: 1.5rem; }
      .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.75rem; }
      .stat-label { color: var(--text-dim); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em; }
      .stat-value { font-size: 1.9rem; font-weight: 700; margin-top: 0.35rem; }
      .actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }
      .action { text-decoration: none; color: inherit; transition: border-color 0.15s ease, transform 0.1s ease; }
      .action:hover { border-color: var(--brand); text-decoration: none; transform: translateY(-2px); }
      .action h3 { color: var(--text); }
    `,
  ],
})
export class DashboardComponent {
  private api = inject(ApiService);
  private auth = inject(AuthService);

  usage = signal<UsageMetrics | null>(null);
  error = signal('');

  name = () => this.auth.me()?.user.email.split('@')[0] ?? '';

  constructor() {
    this.api.get<UsageMetrics>('/analytics/usage').subscribe({
      next: (u) => this.usage.set(u),
      error: () => this.error.set('Could not load usage metrics.'),
    });
  }

  tiles(u: UsageMetrics) {
    return [
      { label: 'Users', value: u.users },
      { label: 'Agents', value: u.agents },
      { label: 'Conversations', value: u.conversations },
      { label: 'Messages', value: u.messages },
      { label: 'Executions', value: u.executions },
      { label: 'Tokens', value: u.tokens_used },
    ];
  }
}
