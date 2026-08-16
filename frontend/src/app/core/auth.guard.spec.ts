// Tests for the route guard.
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  Router,
  RouterStateSnapshot,
  UrlTree,
  provideRouter,
} from '@angular/router';

import { authGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

describe('authGuard', () => {
  function configure(authenticated: boolean) {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        // isAuthenticated is a computed signal on the real service, so the
        // double has to be callable in the same way.
        { provide: AuthService, useValue: { isAuthenticated: signal(authenticated) } },
      ],
    });
  }

  function run() {
    return TestBed.runInInjectionContext(() =>
      authGuard({} as ActivatedRouteSnapshot, { url: '/dashboard' } as RouterStateSnapshot),
    );
  }

  it('lets an authenticated user through', () => {
    configure(true);
    expect(run()).toBeTrue();
  });

  it('sends an anonymous user to /login', () => {
    configure(false);
    const result = run();

    expect(result instanceof UrlTree).toBeTrue();
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/login');
  });
});
