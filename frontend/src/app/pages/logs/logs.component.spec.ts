// Tests for the Logs page.
//
// The behaviour worth pinning here is the one that was wrong: the page used to
// build its rows by requesting /agents/{id}/executions once per agent, so a run
// with no agent attached appeared in none of the responses and was silently
// missing from the log. Chat turns are exactly those runs, and Chat is the main
// way runs are created, so the audit view omitted most of what happened.
//
// The first spec below fails against that old implementation and passes against
// the current one, which is the only reason it is worth writing.
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LogsComponent } from './logs.component';
import { environment } from '../../../environments/environment';

const API = environment.apiBase;

function execution(id: number, agentId: number | null, extra: Record<string, unknown> = {}) {
  return {
    id,
    agent_id: agentId,
    conversation_id: null,
    status: 'completed',
    tokens_used: 10,
    started_at: '2026-08-16T10:00:00',
    finished_at: '2026-08-16T10:00:02',
    ...extra,
  };
}

describe('LogsComponent', () => {
  let fixture: ComponentFixture<LogsComponent>;
  let backend: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LogsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    fixture = TestBed.createComponent(LogsComponent);
    backend = TestBed.inject(HttpTestingController);
  });

  afterEach(() => backend.verify());

  it('includes runs that have no agent attached', () => {
    fixture.detectChanges();

    backend
      .expectOne(`${API}/executions`)
      .flush([execution(3, null), execution(2, 1), execution(1, null)]);
    backend.expectOne(`${API}/agents`).flush([{ id: 1, name: 'Researcher' }]);

    const rows = fixture.componentInstance.rows();
    expect(rows.map((r) => r.id)).toEqual([3, 2, 1]);
    expect(rows.filter((r) => r.agent_id === null).length).toBe(2);
  });

  it('labels an agent-less run rather than leaving the column blank', () => {
    fixture.detectChanges();
    backend.expectOne(`${API}/executions`).flush([execution(1, null)]);
    backend.expectOne(`${API}/agents`).flush([]);

    expect(fixture.componentInstance.rows()[0].agentName).toBe('Chat (no agent)');
  });

  it('resolves agent names from the agent list', () => {
    fixture.detectChanges();
    backend.expectOne(`${API}/executions`).flush([execution(1, 7)]);
    backend.expectOne(`${API}/agents`).flush([{ id: 7, name: 'Researcher' }]);

    expect(fixture.componentInstance.rows()[0].agentName).toBe('Researcher');
  });

  it('falls back to the id when an agent has since been deleted', () => {
    fixture.detectChanges();
    backend.expectOne(`${API}/executions`).flush([execution(1, 99)]);
    backend.expectOne(`${API}/agents`).flush([]);

    expect(fixture.componentInstance.rows()[0].agentName).toBe('Agent #99');
  });

  it('makes one request for the runs, not one per agent', () => {
    fixture.detectChanges();
    backend.expectOne(`${API}/executions`).flush([execution(1, 1)]);
    backend.expectOne(`${API}/agents`).flush([
      { id: 1, name: 'A' },
      { id: 2, name: 'B' },
      { id: 3, name: 'C' },
    ]);

    // Three agents, and still no per-agent execution calls. verify() in
    // afterEach would fail on any that were made.
    expect(backend.match(() => true).length).toBe(0);
  });

  it('still renders the log when the agent list cannot be loaded', () => {
    fixture.detectChanges();
    backend.expectOne(`${API}/executions`).flush([execution(1, 7)]);
    backend.expectOne(`${API}/agents`).flush({}, { status: 500, statusText: 'Server Error' });

    const rows = fixture.componentInstance.rows();
    expect(rows.length).toBe(1);
    expect(rows[0].agentName).toBe('Agent #7');
  });

  it('shows the empty state when nothing has run yet', () => {
    fixture.detectChanges();
    backend.expectOne(`${API}/executions`).flush([]);
    backend.expectOne(`${API}/agents`).flush([]);
    fixture.detectChanges();

    expect(fixture.componentInstance.rows()).toEqual([]);
    expect(fixture.nativeElement.textContent).toContain('No executions yet');
  });

  describe('format', () => {
    // The component loads on construction, so those two requests have to be
    // answered even by tests that only care about a pure helper.
    beforeEach(() => {
      fixture.detectChanges();
      backend.expectOne(`${API}/executions`).flush([]);
      backend.expectOne(`${API}/agents`).flush([]);
    });

    it('renders a valid timestamp as a local string', () => {
      const formatted = fixture.componentInstance.format('2026-08-16T10:00:00');
      expect(formatted).not.toBe('2026-08-16T10:00:00');
      expect(formatted.length).toBeGreaterThan(0);
    });

    it('passes an unparseable value through rather than showing "Invalid Date"', () => {
      expect(fixture.componentInstance.format('not a date')).toBe('not a date');
    });
  });
});
