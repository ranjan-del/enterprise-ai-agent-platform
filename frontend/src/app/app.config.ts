// Application-level providers.
// TODO: checklist "Frontend: Angular pages" — add HTTP client + interceptors.
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
// import { provideHttpClient } from '@angular/common/http';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    // TODO: provideHttpClient(withInterceptors([authInterceptor]))
  ],
};
