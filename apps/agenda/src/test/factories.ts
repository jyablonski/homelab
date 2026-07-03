import type {
  AgendaEvent,
  AgendaFreshness,
  AgendaReminder,
  AgendaTodayResponse,
  Reminder,
} from "@/lib/schemas";

export function makeReminder(overrides: Partial<Reminder> = {}): Reminder {
  return {
    id: 1,
    reminder_type: "car",
    reminder_message: "Get oil changed soon",
    reminder_start_date: "2026-06-01",
    reminder_end_date: null,
    is_completed: false,
    completed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeAgendaReminder(
  overrides: Partial<AgendaReminder> = {},
): AgendaReminder {
  return {
    id: 1,
    type: "car",
    message: "Get oil changed soon",
    start_date: "2026-06-01",
    end_date: null,
    is_completed: false,
    ...overrides,
  };
}

export function makeAgendaEvent(overrides: Partial<AgendaEvent> = {}): AgendaEvent {
  return {
    id: "nba:0022600001",
    source: "nba",
    category: "sports",
    league: "NBA",
    title: "Los Angeles Lakers at Golden State Warriors",
    start_at: "2026-07-03T19:30:00-07:00",
    status: "scheduled",
    metadata: { venue: "Chase Center" },
    ...overrides,
  };
}

export function makeAgendaFreshness(
  overrides: Partial<AgendaFreshness> = {},
): AgendaFreshness {
  return {
    source: "nba",
    last_success_at: "2026-07-03T06:05:00-07:00",
    status: "fresh",
    message: null,
    ...overrides,
  };
}

export function makeAgendaToday(
  overrides: Partial<AgendaTodayResponse> = {},
): AgendaTodayResponse {
  return {
    generated_at: "2026-07-03T15:00:00-07:00",
    timezone: "America/Los_Angeles",
    window: {
      start: "2026-07-03T15:00:00-07:00",
      end: "2026-07-04T15:00:00-07:00",
      due_soon_days: 7,
    },
    reminders: {
      active: [],
      due_soon: [],
      completed: [],
    },
    events: [],
    freshness: [],
    ...overrides,
  };
}
