// Logs: execution history across the workspace's agents.
import { Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { catchError, forkJoin, of } from 'rxjs';
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

  /**
   * Load every run the caller may see.
   *
   * This used to fan out over `/agents/{id}/executions`, one request per agent,
   * and the result was an audit page that silently omitted things. A chat turn
   * with no agent attached belongs to no agent, so it appeared in none of those
   * responses: the Chat page is the main way runs are created, and none of them
   * were ever listed. A log that quietly drops rows is worse than no log,
   * because it is read as complete.
   *
   * `/executions` is the endpoint that already answers this question, with the
   * org and member visibility rules applied server-side. It is also one request
   * instead of N, and it cannot skew if an agent is deleted mid-load.
   */
  constructor() {
    forkJoin({
      executions: this.api.get<Execution[]>('/executions'),
      // Only used to turn agent_id into a readable name. A failure here must
      // not take the log itself down, so it degrades to an empty list.
      agents: this.api.get<Agent[]>('/agents').pipe(catchError(() => of([] as Agent[]))),
    }).subscribe(({ executions, agents }) => {
      const names = new Map(agents.map((a) => [a.id, a.name]));
      this.rows.set(
        executions.map((e) => ({
          ...e,
          agentName:
            e.agent_id === null
              ? 'Chat (no agent)'
              : names.get(e.agent_id) ?? `Agent #${e.agent_id}`,
        })),
      );
    });
  }

  format(iso: string): string {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleString();
  }
}
