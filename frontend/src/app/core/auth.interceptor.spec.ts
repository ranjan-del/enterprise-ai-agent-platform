// Tests for the auth interceptor.
//
// The subtle rule is the last one: a 401 only means "your session is over" if
// you actually sent a session. A 401 on an anonymous request is the login form
// being told the password was wrong, and treating that as an expiry would
// bounce the user to the page they are already on.
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';
import { environment } from '../../environments/environment';

const API = environment.apiBase;

describe('authInterceptor', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    localStorage.clear();
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
      ],
    });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    backend.verify();
    localStorage.clear();
  });

  function signIn(token = 'access-1') {
    localStorage.setItem('eap_access', token);
    TestBed.inject(AuthService); // constructed with the token already in place
  }

  it('attaches the bearer token when there is a session', () => {
    signIn();
    http.get(`${API}/agents`).subscribe();
    const req = backend.expectOne(`${API}/agents`);

    expect(req.request.headers.get('Authorization')).toBe('Bearer access-1');
    req.flush([]);
  });

  it('sends no Authorization header when there is no session', () => {
    http.post(`${API}/auth/login`, {}).subscribe({ error: () => {} });
    const req = backend.expectOne(`${API}/auth/login`);

    expect(req.request.headers.has('Authorization')).toBeFalse();
    req.flush({}, { status: 401, statusText: 'Unauthorized' });
  });

  it('logs out and redirects when an authenticated request comes back 401', () => {
    signIn();
    http.get(`${API}/agents`).subscribe({ error: () => {} });
    backend.expectOne(`${API}/agents`).flush({}, { status: 401, statusText: 'Unauthorized' });

    expect(localStorage.getItem('eap_access')).toBeNull();
    expect(router.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('does not redirect on a 401 for an anonymous request', () => {
    http.post(`${API}/auth/login`, {}).subscribe({ error: () => {} });
    backend.expectOne(`${API}/auth/login`).flush({}, { status: 401, statusText: 'Unauthorized' });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('leaves a 403 alone, because the session is valid and the role is not', () => {
    signIn();
    let status = 0;
    http.get(`${API}/orgs/users`).subscribe({ error: (e) => (status = e.status) });
    backend
      .expectOne(`${API}/orgs/users`)
      .flush({ detail: 'Forbidden' }, { status: 403, statusText: 'Forbidden' });

    expect(status).toBe(403);
    expect(router.navigate).not.toHaveBeenCalled();
    expect(localStorage.getItem('eap_access')).toBe('access-1');
  });

  it('passes a 500 through without ending the session', () => {
    signIn();
    let status = 0;
    http.get(`${API}/agents`).subscribe({ error: (e) => (status = e.status) });
    backend.expectOne(`${API}/agents`).flush({}, { status: 500, statusText: 'Server Error' });

    expect(status).toBe(500);
    expect(localStorage.getItem('eap_access')).toBe('access-1');
  });
});
