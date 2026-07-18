// Root shell component.
// TODO: checklist "Frontend: Angular pages" — add nav/layout chrome.
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <!-- TODO: sidebar + topbar layout wrapping <router-outlet> -->
    <router-outlet></router-outlet>
  `,
})
export class AppComponent {
  title = 'enterprise-ai-agent-platform';
}
