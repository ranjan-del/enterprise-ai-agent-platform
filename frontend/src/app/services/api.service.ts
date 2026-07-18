// Base API client wrapper around the backend REST surface.
// TODO: checklist "API documentation" — typed methods per endpoint.
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ApiService {
  // TODO: inject HttpClient; read base URL from environment.
  readonly baseUrl = '/api/v1';

  // TODO: get<T>(path), post<T>(path, body), etc.
}
