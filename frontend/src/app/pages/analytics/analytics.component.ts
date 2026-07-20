// Analytics: execution outcomes and tool-usage breakdown.
import { Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { ExecutionAnalytics } from '../../models';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <header class="page-head"><h1>Analytics</h1><p>Execution outcomes and tool usage.</p></header>

    <section class="stats" *ngIf="data() as d">
      <div class="card stat"><div class="stat-label">Executions</div><div class="stat-value">{{ d.total_executions }}</div></div>
      <div class="card stat"><div class="stat-label">Completed</div><div class="stat-value">{{ d.completed }}</div></div>
      <div class="card stat"><div class="stat-label">Failed</div><div class="stat-value">{{ d.failed }}</div></div>
      <div class="card stat"><div class="stat-label">Tokens</div><div class="stat-value">{{ d.tokens_used }}</div></div>
    </section>

    <section class="card" *ngIf="data() as d">
      <h3>Tool usage</h3>
      <p class="muted" *ngIf="tools(d).length === 0">No tools have been used yet.</p>
      <div class="bar-row" *ngFor="let t of tools(d)">
        <span class="bar-label">{{ t.name }}</span>
        <div class="bar-track"><div class="bar-fill" [style.width.%]="pct(d, t.count)"></div></div>
        <span class="bar-value">{{ t.count }}</span>
      </div>
    </section>
  `,
  styles: [
    `
      .page-head { margin-bottom: 1.25rem; }
      .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
      .stat-label { color: var(--text-dim); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; }
      .stat-value { font-size: 1.8rem; font-weight: 700; margin-top: 0.3rem; }
      .bar-row { display: grid; grid-template-columns: 120px 1fr 40px; align-items: center; gap: 0.75rem; margin-bottom: 0.6rem; }
      .bar-label { font-size: 0.9rem; }
      .bar-track { height: 10px; background: var(--bg-elev-2); border-radius: 999px; overflow: hidden; }
      .bar-fill { height: 100%; background: var(--brand); border-radius: 999px; min-width: 2px; }
      .bar-value { text-align: right; color: var(--text-dim); font-size: 0.85rem; }
    `,
  ],
})
export class AnalyticsComponent {
  private api = inject(ApiService);
  data = signal<ExecutionAnalytics | null>(null);

  constructor() {
    this.api.get<ExecutionAnalytics>('/analytics/executions').subscribe((d) => this.data.set(d));
  }

  tools(d: ExecutionAnalytics): { name: string; count: number }[] {
    return Object.entries(d.tool_usage)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }

  pct(d: ExecutionAnalytics, count: number): number {
    const max = Math.max(1, ...Object.values(d.tool_usage));
    return (count / max) * 100;
  }
}
