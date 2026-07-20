// Root shell: responsive sidebar + topbar around the routed page. Chrome is
// hidden on the login route and for unauthenticated visitors.
import { Component, computed, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { AuthService } from './services/auth.service';

interface NavItem {
  label: string;
  path: string;
  icon: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NgFor, NgIf],
  template: `
    <div class="shell" [class.bare]="!showChrome()">
      <aside class="sidebar" *ngIf="showChrome()" [class.open]="menuOpen()">
        <div class="brand">
          <span class="logo" aria-hidden="true">◆</span>
          <span class="brand-name">Agent Platform</span>
        </div>
        <nav>
          <a
            *ngFor="let item of nav"
            [routerLink]="item.path"
            routerLinkActive="active"
            (click)="menuOpen.set(false)"
          >
            <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
            {{ item.label }}
          </a>
        </nav>
        <div class="sidebar-foot">
          <div class="org" *ngIf="auth.me() as m">
            <div class="org-name">{{ m.org.name }}</div>
            <div class="org-email">{{ m.user.email }}</div>
            <span class="badge">{{ m.user.role }}</span>
          </div>
          <button class="btn ghost sm block" (click)="logout()">Sign out</button>
        </div>
      </aside>

      <div class="main">
        <header class="topbar" *ngIf="showChrome()">
          <button class="menu-btn btn ghost sm" (click)="toggleMenu()" aria-label="Toggle navigation">☰</button>
          <div class="topbar-title">{{ currentTitle() }}</div>
        </header>
        <main class="content"><router-outlet></router-outlet></main>
      </div>

      <div class="scrim" *ngIf="showChrome() && menuOpen()" (click)="menuOpen.set(false)"></div>
    </div>
  `,
  styles: [
    `
      .shell { display: flex; min-height: 100vh; }
      .shell.bare { display: block; }

      .sidebar {
        width: 240px; flex-shrink: 0;
        background: var(--bg-elev);
        border-right: 1px solid var(--border);
        display: flex; flex-direction: column;
        padding: 1rem 0.75rem;
        position: sticky; top: 0; height: 100vh;
      }
      .brand { display: flex; align-items: center; gap: 0.6rem; padding: 0.5rem 0.6rem 1rem; }
      .logo { color: var(--brand); font-size: 1.2rem; }
      .brand-name { font-weight: 700; letter-spacing: -0.01em; }
      nav { display: flex; flex-direction: column; gap: 0.15rem; flex: 1; }
      nav a {
        display: flex; align-items: center; gap: 0.7rem;
        padding: 0.6rem 0.7rem; border-radius: var(--radius-sm);
        color: var(--text-dim); font-weight: 500; text-decoration: none;
      }
      nav a:hover { background: var(--bg-elev-2); color: var(--text); text-decoration: none; }
      nav a.active { background: var(--brand-soft); color: var(--brand); }
      .nav-icon { width: 1.2rem; text-align: center; }

      .sidebar-foot { border-top: 1px solid var(--border); padding-top: 0.75rem; display: flex; flex-direction: column; gap: 0.6rem; }
      .org-name { font-weight: 600; font-size: 0.9rem; }
      .org-email { font-size: 0.78rem; color: var(--text-faint); margin-bottom: 0.3rem; }

      .main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
      .topbar {
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.8rem 1.25rem; border-bottom: 1px solid var(--border);
        background: rgba(11,13,18,0.7); backdrop-filter: blur(8px);
        position: sticky; top: 0; z-index: 5;
      }
      .topbar-title { font-weight: 650; }
      .menu-btn { display: none; }
      .content { padding: 1.5rem; flex: 1; max-width: 1200px; width: 100%; }

      .scrim { display: none; }

      @media (max-width: 820px) {
        .sidebar {
          position: fixed; z-index: 20; left: 0; top: 0;
          transform: translateX(-100%); transition: transform 0.2s ease;
        }
        .sidebar.open { transform: translateX(0); }
        .menu-btn { display: inline-flex; }
        .scrim { display: block; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 15; }
      }
    `,
  ],
})
export class AppComponent {
  auth = inject(AuthService);
  private router = inject(Router);

  menuOpen = signal(false);
  private currentUrl = signal(this.router.url);

  nav: NavItem[] = [
    { label: 'Dashboard', path: '/dashboard', icon: '▤' },
    { label: 'Chat', path: '/chat', icon: '✦' },
    { label: 'Agents', path: '/agents', icon: '◈' },
    { label: 'Logs', path: '/logs', icon: '≣' },
    { label: 'Analytics', path: '/analytics', icon: '◔' },
    { label: 'Settings', path: '/settings', icon: '⚙' },
  ];

  showChrome = computed(() => this.auth.isAuthenticated() && !this.currentUrl().startsWith('/login'));
  currentTitle = computed(() => {
    const url = this.currentUrl().split('?')[0];
    const item = this.nav.find((n) => url.startsWith(n.path));
    return item ? item.label : 'Workspace';
  });

  constructor() {
    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e) => this.currentUrl.set(e.urlAfterRedirects));

    if (this.auth.isAuthenticated() && !this.auth.me()) {
      this.auth.loadMe().subscribe({ error: () => {} });
    }
  }

  toggleMenu(): void {
    this.menuOpen.update((v) => !v);
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
