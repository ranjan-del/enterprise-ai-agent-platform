// Agents page: list existing agents and create new ones with tool selection.
import { Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Agent, Tool } from '../../models';

@Component({
  selector: 'app-agents',
  standalone: true,
  imports: [NgFor, NgIf, FormsModule],
  template: `
    <header class="page-head">
      <h1>Agents</h1>
      <p>Configure assistants and the offline tools they can call.</p>
    </header>

    <div class="grid">
      <section class="list">
        <div class="card agent" *ngFor="let a of agents()">
          <div class="agent-head">
            <h3>{{ a.name }}</h3>
            <button class="btn ghost sm" (click)="remove(a)" aria-label="Delete agent">✕</button>
          </div>
          <p>{{ a.description || 'No description.' }}</p>
          <div class="tools">
            <span class="badge" *ngFor="let t of a.tools">{{ t }}</span>
            <span class="muted" *ngIf="a.tools.length === 0">No tools enabled</span>
          </div>
        </div>
        <p class="muted" *ngIf="agents().length === 0">No agents yet. Create one on the right.</p>
      </section>

      <aside class="card create">
        <h3>New agent</h3>
        <div class="field">
          <label for="an">Name</label>
          <input id="an" class="input" [(ngModel)]="name" name="an" />
        </div>
        <div class="field">
          <label for="ad">Description</label>
          <input id="ad" class="input" [(ngModel)]="description" name="ad" />
        </div>
        <div class="field">
          <label>Tools</label>
          <label class="tool-opt" *ngFor="let t of tools()">
            <input type="checkbox" [checked]="selected.has(t.name)" (change)="toggle(t.name)" />
            <span><strong>{{ t.name }}</strong> — {{ t.description }}</span>
          </label>
        </div>
        <p class="error-text" *ngIf="error()">{{ error() }}</p>
        <button class="btn block" (click)="create()" [disabled]="!name.trim()">Create agent</button>
      </aside>
    </div>
  `,
  styles: [
    `
      .page-head { margin-bottom: 1.25rem; }
      .grid { display: grid; grid-template-columns: 1fr 340px; gap: 1.25rem; align-items: start; }
      .list { display: flex; flex-direction: column; gap: 1rem; }
      .agent-head { display: flex; justify-content: space-between; align-items: center; }
      .tools { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
      .tool-opt { display: flex; gap: 0.55rem; align-items: flex-start; font-size: 0.85rem; color: var(--text-dim);
        margin-bottom: 0.5rem; cursor: pointer; }
      .tool-opt input { margin-top: 0.2rem; }
      @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
    `,
  ],
})
export class AgentsComponent {
  private api = inject(ApiService);

  agents = signal<Agent[]>([]);
  tools = signal<Tool[]>([]);
  selected = new Set<string>();
  name = '';
  description = '';
  error = signal('');

  constructor() {
    this.reload();
    this.api.get<Tool[]>('/tools').subscribe((t) => this.tools.set(t));
  }

  reload(): void {
    this.api.get<Agent[]>('/agents').subscribe((a) => this.agents.set(a));
  }

  toggle(name: string): void {
    if (this.selected.has(name)) this.selected.delete(name);
    else this.selected.add(name);
  }

  create(): void {
    this.error.set('');
    this.api
      .post<Agent>('/agents', {
        name: this.name,
        description: this.description,
        tools: Array.from(this.selected),
      })
      .subscribe({
        next: () => {
          this.name = '';
          this.description = '';
          this.selected.clear();
          this.reload();
        },
        error: (err) => this.error.set(err?.error?.detail ? String(err.error.detail) : 'Could not create agent (need owner/admin role).'),
      });
  }

  remove(a: Agent): void {
    this.api.delete(`/agents/${a.id}`).subscribe({
      next: () => this.reload(),
      error: () => this.error.set('Could not delete agent.'),
    });
  }
}
