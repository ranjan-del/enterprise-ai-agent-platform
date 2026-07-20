// Logs: execution history across the workspace's agents.
import { Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { forkJoin, of } from 'rxjs';
import { ApiService } from '../../services/api.service';
import { Agent, Execution } from '../../models';

interface Row extends Execution {
  agentName: string;
}

@Component({
  selector: 'app-logs',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <header class="page-head"><h1>Execution logs</h1><p>Every agent run and its outcome.</p></header>

    <div class="card">
      <table class="tbl" *ngIf="rows().length; else empty">
        <thead>
          <tr><th>#</th><th>Agent</th><th>Status</th><th>Tokens</th><th>Started</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let r of rows()">
            <td>{{ r.id }}</td>
            <td>{{ r.agentName }}</td>
            <td><span class="badge" [style.color]="r.status === 'completed' ? 'var(--success)' : 'var(--danger)'">{{ r.status }}</span></td>
            <td>{{ r.tokens_used }}</td>
            <td>{{ format(r.started_at) }}</td>
          </tr>
        </tbody>
      </table>
      <ng-template #empty><p class="muted">No executions yet. Run an agent from the Chat or Agents page.</p></ng-template>
    </div>
  `,
  styles: [
    `
      .page-head { margin-bottom: 1.25rem; }
      .tbl { width: 100%; border-collapse: collapse; }
      .tbl th, .tbl td { text-align: left; padding: 0.55rem 0.4rem; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
      .tbl th { color: var(--text-dim); font-weight: 600; }
    `,
  ],
})
export class LogsComponent {
  private api = inject(ApiService);
  rows = signal<Row[]>([]);

  constructor() {
    this.api.get<Agent[]>('/agents').subscribe((agents) => {
      if (!agents.length) return;
      const calls = agents.map((a) => this.api.get<Execution[]>(`/agents/${a.id}/executions`));
      forkJoin(calls.length ? calls : [of([] as Execution[])]).subscribe((results) => {
        const rows: Row[] = [];
        results.forEach((execs, i) => {
          for (const e of execs) rows.push({ ...e, agentName: agents[i].name });
        });
        rows.sort((a, b) => b.id - a.id);
        this.rows.set(rows);
      });
    });
  }

  format(iso: string): string {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleString();
  }
}
