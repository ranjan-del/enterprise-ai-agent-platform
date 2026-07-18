// Authentication + session state.
// TODO: checklist "Auth + multi-tenancy: JWT".
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthService {
  // TODO: login(email, password) -> stores JWT, tracks current org/user.
  // TODO: logout(), isAuthenticated(), token getter.
}
