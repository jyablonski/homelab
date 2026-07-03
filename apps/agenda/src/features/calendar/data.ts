import type { PersonalCalendarEvent } from "@/features/calendar/types";

/**
 * Placeholder personal-calendar schedule. There is no backend for this yet
 * (see notes/ideas/frontend-app.md); this is static frontend-only fixture
 * data until a real calendar integration lands.
 */
export function getPersonalCalendarEvents(): PersonalCalendarEvent[] {
  return [
    { id: "standup", title: "Standup", startTime: "08:00", endTime: "08:20" },
    { id: "dentist", title: "Dentist appointment", startTime: "10:00", endTime: "10:45" },
    { id: "team-sync", title: "Team sync", startTime: "14:00", endTime: "14:30" },
    { id: "gym", title: "Gym", startTime: "18:00", endTime: "19:00" },
  ];
}
