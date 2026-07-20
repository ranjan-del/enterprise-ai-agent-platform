// Login / register page. Also offers a one-click demo sign-in.
import { Component, inject, signal } from '@angular/core';
import { NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [NgIf, FormsModule],
  template: `
    <div class="auth-wrap">
      <div class="auth-card card">
        <div class="head">
          <span class="logo" aria-hidden="true">◆</span>
          <h1>{{ mode() === 'login' ? 'Welcome back' : 'Create your workspace' }}</h1>
          <p>{{ mode() === 'login' ? 'Sign in to your agent workspace.' : 'Spin up a new organization in seconds.' }}</p>
        </div>

        <form (ngSubmit)="submit()">
          <div class="field" *ngIf="mode() === 'register'">
            <label for="org">Organization name</label>
            <input id="org" class="input" name="org" [(ngModel)]="orgName" required autocomplete="organization" />
          </div>
          <div class="field">
            <label for="email">Email</label>
            <input id="email" class="input" type="email" name="email" [(ngModel)]="email" required autocomplete="email" />
          </div>
          <div class="field">
            <label for="password">Password</label>
            <input id="password" class="input" type="password" name="password" [(ngModel)]="password" required autocomplete="current-password" />
          </div>

          <p class="error-text" *ngIf="error()">{{ error() }}</p>

          <button class="btn block" type="submit" [disabled]="loading()">
            <span class="spinner" *ngIf="loading()"></span>
            {{ mode() === 'login' ? 'Sign in' : 'Create workspace' }}
          </button>
        </form>

        <button class="btn secondary block" (click)="demo()" [disabled]="loading()">Try the demo account</button>

        <p class="switch">
          {{ mode() === 'login' ? "New here?" : 'Already have an account?' }}
          <a href="#" (click)="toggle($event)">{{ mode() === 'login' ? 'Create a workspace' : 'Sign in' }}</a>
        </p>
      </div>
    </div>
  `,
  styles: [
    `
      .auth-wrap { min-height: 100vh; display: grid; place-items: center; padding: 1.5rem;
        background: radial-gradient(1200px 600px at 50% -10%, rgba(99,102,241,0.18), transparent); }
      .auth-card { width: 100%; max-width: 400px; }
      .head { text-align: center; margin-bottom: 1.25rem; }
      .logo { font-size: 2rem; color: var(--brand); }
      h1 { margin-top: 0.5rem; }
      .switch { text-align: center; margin: 1rem 0 0; font-size: 0.9rem; color: var(--text-dim); }
      .btn.secondary { margin-top: 0.6rem; }
    `,
  ],
})
export class LoginComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  mode = signal<'login' | 'register'>('login');
  loading = signal(false);
  error = signal('');

  orgName = '';
  email = '';
  password = '';

  toggle(e: Event): void {
    e.preventDefault();
    this.error.set('');
    this.mode.update((m) => (m === 'login' ? 'register' : 'login'));
  }

  submit(): void {
    this.error.set('');
    this.loading.set(true);
    const done = {
      next: () => this.afterAuth(),
      error: (err: any) => {
        this.loading.set(false);
        this.error.set(err?.error?.detail ? String(err.error.detail) : 'Something went wrong. Please try again.');
      },
    };
    if (this.mode() === 'login') {
      this.auth.login(this.email, this.password).subscribe(done);
    } else {
      this.auth.register(this.orgName, this.email, this.password).subscribe(done);
    }
  }

  demo(): void {
    this.error.set('');
    this.loading.set(true);
    this.auth.login('demo@acme.com', 'demopass123').subscribe({
      next: () => this.afterAuth(),
      error: () => {
        this.loading.set(false);
        this.error.set('Demo account unavailable. Start the backend with SEED_DEMO_DATA enabled.');
      },
    });
  }

  private afterAuth(): void {
    this.auth.loadMe().subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.loading.set(false);
        this.router.navigate(['/dashboard']);
      },
    });
  }
}
