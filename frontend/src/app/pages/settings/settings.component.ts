// Settings: organization details plus user management (owner/admin).
import { Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [NgFor, NgIf, FormsModule],
  template: `
    <header class="page-head"><h1>Settings</h1><p>Manage your organization and team.</p></header>

    <section class="card" *ngIf="auth.me() as m">
      <h3>Organization</h3>
      <div class="rows">
        <div><span class="muted">Name</span><span>{{ m.org.name }}</span></div>
        <div><span class="muted">Slug</span><span>{{ m.org.slug }}</span></div>
        <div><span class="muted">Plan</span><span class="badge">{{ m.org.plan }}</span></div>
        <div><span class="muted">Your role</span><span class="badge">{{ m.user.role }}</span></div>
      </div>
    </section>

    <section class="card">
      <h3>Team members</h3>
      <table class="tbl">
        <thead><tr><th>Email</th><th>Role</th><th>Status</th></tr></thead>
        <tbody>
          <tr *ngFor="let u of users()">
            <td>{{ u.email }}</td>
            <td><span class="badge">{{ u.role }}</span></td>
            <td>{{ u.is_active ? 'Active' : 'Disabled' }}</td>
          </tr>
        </tbody>
      </table>

      <div class="add-user">
        <h4>Invite a member</h4>
        <div class="add-row">
          <input class="input" placeholder="email@company.com" [(ngModel)]="email" name="e" />
          <input class="input" type="password" placeholder="temp password (8+ chars)" [(ngModel)]="password" name="p" />
          <select class="input" [(ngModel)]="role" name="r">
            <option value="member">member</option>
            <option value="admin">admin</option>
          </select>
          <button class="btn" (click)="add()" [disabled]="!email || password.length < 8">Add</button>
        </div>
        <p class="error-text" *ngIf="error()">{{ error() }}</p>
      </div>
    </section>
  `,
  styles: [
    `
      .page-head { margin-bottom: 1.25rem; }
      .card { margin-bottom: 1.25rem; }
      .rows { display: grid; gap: 0.6rem; }
      .rows > div { display: flex; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; }
      .tbl { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
      .tbl th, .tbl td { text-align: left; padding: 0.55rem 0.4rem; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
      .tbl th { color: var(--text-dim); font-weight: 600; }
      .add-user { border-top: 1px solid var(--border); padding-top: 1rem; }
      .add-row { display: grid; grid-template-columns: 1.5fr 1.5fr 1fr auto; gap: 0.5rem; }
      @media (max-width: 700px) { .add-row { grid-template-columns: 1fr; } }
    `,
  ],
})
export class SettingsComponent {
  private api = inject(ApiService);
  auth = inject(AuthService);

  users = signal<User[]>([]);
  email = '';
  password = '';
  role = 'member';
  error = signal('');

  constructor() {
    this.reload();
    if (!this.auth.me()) this.auth.loadMe().subscribe({ error: () => {} });
  }

  reload(): void {
    this.api.get<User[]>('/users').subscribe((u) => this.users.set(u));
  }

  add(): void {
    this.error.set('');
    this.api.post<User>('/users', { email: this.email, password: this.password, role: this.role }).subscribe({
      next: () => {
        this.email = '';
        this.password = '';
        this.reload();
      },
      error: (err) => this.error.set(err?.error?.detail ? String(err.error.detail) : 'Could not add member (need owner/admin role).'),
    });
  }
}
