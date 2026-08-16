// Tests for AuthService: token persistence and the signals the shell reads.
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

const API = environment.apiBase;

const TOKENS = { access_token: 'access-1', refresh_token: 'refresh-1', token_type: 'bearer' };

describe('AuthService', () => {
  let service: AuthService;
  let backend: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    backend = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    backend.verify();
    localStorage.clear();
  });

  it('starts unauthenticated with an empty store', () => {
    expect(service.isAuthenticated()).toBeFalse();
    expect(service.getAccessToken()).toBeNull();
    expect(service.me()).toBeNull();
  });

  it('stores both tokens on login and flips isAuthenticated', () => {
    service.login('demo@acme.com', 'demopass123').subscribe();
    const req = backend.expectOne(`${API}/auth/login`);
    expect(req.request.body).toEqual({ email: 'demo@acme.com', password: 'demopass123' });
    req.flush(TOKENS);

    expect(service.getAccessToken()).toBe('access-1');
    expect(localStorage.getItem('eap_refresh')).toBe('refresh-1');
    expect(service.isAuthenticated()).toBeTrue();
  });

  it('registers an org and signs the new owner straight in', () => {
    service.register('Acme Inc', 'owner@acme.com', 'pw').subscribe();
    const req = backend.expectOne(`${API}/auth/register`);
    expect(req.request.body).toEqual({
      org_name: 'Acme Inc',
      email: 'owner@acme.com',
      password: 'pw',
    });
    req.flush(TOKENS);

    expect(service.isAuthenticated()).toBeTrue();
  });

  it('leaves the session untouched when login is rejected', () => {
    service.login('demo@acme.com', 'wrong').subscribe({ error: () => {} });
    backend
      .expectOne(`${API}/auth/login`)
      .flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });

    expect(service.isAuthenticated()).toBeFalse();
    expect(localStorage.getItem('eap_access')).toBeNull();
  });

  it('caches the current user on loadMe', () => {
    const me = { id: 1, email: 'demo@acme.com', role: 'owner', org_id: 1, org_name: 'Acme Inc' };
    service.loadMe().subscribe();
    backend.expectOne(`${API}/auth/me`).flush(me);

    expect(service.me()).toEqual(me as never);
  });

  it('clears every trace of the session on logout', () => {
    service.login('demo@acme.com', 'pw').subscribe();
    backend.expectOne(`${API}/auth/login`).flush(TOKENS);
    service.loadMe().subscribe();
    backend.expectOne(`${API}/auth/me`).flush({ id: 1, email: 'demo@acme.com' });

    service.logout();

    expect(service.isAuthenticated()).toBeFalse();
    expect(service.me()).toBeNull();
    expect(localStorage.getItem('eap_access')).toBeNull();
    expect(localStorage.getItem('eap_refresh')).toBeNull();
  });

  it('rehydrates the session from storage on a page reload', () => {
    localStorage.setItem('eap_access', 'access-from-last-time');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });

    const reloaded = TestBed.inject(AuthService);
    expect(reloaded.isAuthenticated()).toBeTrue();
    expect(reloaded.getAccessToken()).toBe('access-from-last-time');

    backend = TestBed.inject(HttpTestingController);
  });
});
