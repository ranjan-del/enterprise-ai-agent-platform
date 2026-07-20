// Authentication + session state. Persists tokens in localStorage and exposes
// the current user/org as a signal for the shell to react to.
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { ApiService } from './api.service';
import { Me, Token } from '../models';

const ACCESS_KEY = 'eap_access';
const REFRESH_KEY = 'eap_refresh';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private api = inject(ApiService);

  readonly me = signal<Me | null>(null);
  readonly isAuthenticated = computed(() => !!this.token());

  private _token = signal<string | null>(localStorage.getItem(ACCESS_KEY));
  token = this._token.asReadonly();

  login(email: string, password: string): Observable<Token> {
    return this.api
      .post<Token>('/auth/login', { email, password })
      .pipe(tap((t) => this.store(t)));
  }

  register(org_name: string, email: string, password: string): Observable<Token> {
    return this.api
      .post<Token>('/auth/register', { org_name, email, password })
      .pipe(tap((t) => this.store(t)));
  }

  loadMe(): Observable<Me> {
    return this.api.get<Me>('/auth/me').pipe(tap((m) => this.me.set(m)));
  }

  logout(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    this._token.set(null);
    this.me.set(null);
  }

  getAccessToken(): string | null {
    return this._token();
  }

  private store(t: Token): void {
    localStorage.setItem(ACCESS_KEY, t.access_token);
    localStorage.setItem(REFRESH_KEY, t.refresh_token);
    this._token.set(t.access_token);
  }
}
