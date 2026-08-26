# Generalisation: from one person's planner to anyone's

Status: approved, not yet implemented
Date: 2026-08-26

## Context

ShiftScan works, but it is built around one person. Five hard-coded activities live in
`ACTIVITY_MAP`, the timezone is a literal `Europe/Istanbul`, day names are a Turkish list
in `timeline_builder`, ICS summaries say `Vardiya` and `Uyku`, and the Gemini prompt
carries rules written for those five specific activities ("Spor can be early morning",
"Sosyal must never be 04:00-08:00").

The reliability work is done — four rounds fixed day-off planning, LLM output validation,
OCR hardening, error leakage, ICS RFC 5545 compliance, sleep placement and the night
filter. This is the round that makes the app usable by someone who is not its author.

## Goals

- A user defines their own activities: name, weekly amount, unit, preferred time of day.
- The backend carries no Turkish strings and no hard-coded activity knowledge.
- Timezone comes from the browser instead of a literal.
- Translations live in exactly one place (`static/js/i18n.js`).

## Non-goals

- No server-side storage, accounts or profiles. The app stays stateless; the README's
  privacy claim ("nothing is stored") must remain true.
- No config file on the server. Nobody self-hosts this yet.
- The language picker's own gaps (fixed `lang="tr"`, unaudited translations) are a
  separate round.
- Backlog items 5, 8, 10 and 12 are untouched.

## Decisions

1. **Configuration travels in the request.** Everything the planner needs — activities,
   timezone, calendar labels — arrives with each `POST /generate-plan`. The frontend keeps
   the user's list in `localStorage`.
2. **Activities are user-defined, with a default template.** First load shows the five
   activities that used to be hard-coded — content production, sports, reading, social,
   gaming — but now as ordinary editable rows, named from i18n. Every entry can be
   renamed or deleted, and the defaults carry no special status in the code.
3. **Placement preference is a structured choice**, not free text: morning / afternoon /
   evening / any. The user never writes into the prompt, so there is nothing to sanitise.
4. **The model answers with indices and ids**, not names. Day 0-6, activity id. The
   current fuzzy name matching cannot survive user-defined names and is removed.

## API contract

```json
POST /generate-plan
{
  "start_date": "2026-08-24",
  "timezone": "Europe/Berlin",
  "labels": { "shift": "Schicht", "sleep": "Schlaf" },
  "shift_events": [
    { "start": "2026-08-24T09:00:00+02:00", "end": "2026-08-24T18:00:00+02:00" }
  ],
  "activities": [
    { "id": "a1", "name": "Sport", "amount": 3, "unit": "days",  "preferred": "morning" },
    { "id": "a2", "name": "Guitar", "amount": 2, "unit": "hours", "preferred": "any" }
  ]
}
```

### Validation

| Field | Rule |
|---|---|
| `timezone` | Resolvable by `pytz`; unknown zone → HTTP 400 |
| `labels.shift`, `labels.sleep` | 1-80 chars; default `"Shift"` / `"Sleep"` |
| `activities` | List, 1-20 entries; order is the user's order |
| `activities[].id` | 1-64 chars, unique within the request |
| `activities[].name` | 1-80 chars |
| `activities[].amount` | `0 < amount <= 168` |
| `activities[].unit` | `Literal["hours", "days"]` |
| `activities[].preferred` | `Literal["morning", "afternoon", "evening", "any"]`, default `"any"` |

`activities` changes from a dict to a list. A dict cannot express order and forces the
key to double as an identifier.

### Removed fields

`shift_text`, `ShiftEvent.title` and `ShiftEvent.original_line` are dropped from the
request. The backend never reads them; the frontend uses `original_line` locally for the
ICS description it builds itself. Since the contract is breaking anyway, it is the moment
to stop sending shift text the server has no use for.

### Semantics of `unit`

- `hours`: total hours for the week.
- `days`: number of distinct days per week, one session each, `DEFAULT_SESSION_HOURS = 1.0`
  per session.

The current code multiplies days by 1 with a comment admitting the assumption. This spec
promotes that assumption to a named constant instead of leaving it implicit.

## Backend changes

### `services/timeline_builder.py`

- `DAY_NAMES` deleted.
- `build_timeline(shift_events, timezone)` and `find_free_slots(timeline, week_start, timezone)`
  take the zone as a parameter. Both need it: the first to normalise incoming ISO
  timestamps to local time, the second to build day boundaries with `datetime.combine`.
- `find_free_slots` returns `(day_index, start, end)` where 0 is Monday, matching the
  order of the deleted list.
- `NIGHT_END_HOUR` stays a constant. It encodes a human rule, not a user preference.

### `services/ai_planner.py`

- `ACTIVITY_MAP` deleted, along with the per-activity rules in the prompt.
- Prompt building takes `List[ActivityGoal]`.
- `ActivityPlanItem` becomes `day_index: int` (0-6), `activity_id: str`, `hours: float`.
- `parse_activity_plan(raw, known_ids)` drops rows whose id is unknown or whose index is
  out of range, alongside the existing type and bound checks.
- `apply_activity_plan` matches on `day_index` and looks the display name up from the
  request's activities.
- `generate_basic_plan` honours `preferred`: it tries slots inside the preferred window
  first and falls back to any free slot when the activity does not fit there. Falling
  back silently is acceptable here — reporting unplaceable hours is backlog item 8.

### `services/ics_generator.py`

`generate_final_ics(timeline, activity_events, labels)`. The `"Vardiya"` / `"Uyku"`
literals are replaced by the request's labels. Escaping is already in place, so a user
activity called `Guitar; practice` is safe.

### `main.py`

New Pydantic models (`ActivityGoal`, `CalendarLabels`, revised `PlanRequest`), timezone
validation, and the plumbing to pass labels and timezone through.

## Prompt contract

The prompt is written in English. Activity names pass through as the user typed them;
the model is told to return ids, never names.

```
FREE TIME (day index 0 = Monday):
- day 0: 7.5 hours free
- day 1: 4.0 hours free

ACTIVITY GOALS:
- id a1 "Sport": 3 days per week, 1 hour each, prefer morning (06:00-12:00)
- id a2 "Guitar": 2 hours per week, no time preference

RULES:
- Do not overlap activities.
- Keep activities in waking hours; avoid 01:00-06:00.
- Respect each activity's preferred window when the free time allows it.
- Do not schedule demanding activities right after a shift ends.

Return ONLY JSON:
[{"day_index": 0, "activity_id": "a1", "hours": 1}]
```

Preferred windows: morning 06:00-12:00, afternoon 12:00-18:00, evening 18:00-23:00,
`any` imposes nothing. These bounds are constants, not user settings.

## Frontend

### `templates/index.html`

The five checkbox blocks are replaced by an empty `<ul id="activity-list">`, an "add"
button, and a `<template>` for a row: name input, amount input, unit select, preferred
select, delete button.

### `static/js/activities.js` (new)

Activity list state — defaults, add, remove, edit, `localStorage` persistence under
`shiftscan-activities-v1`, and building the request payload. Exported the same way as
`ics.js` (`window.ShiftScanActivities` in the browser, `module.exports` under Node) so it
is testable with `node --test`. Keeping this logic inside the `app.js` closure would make
it untestable, which is exactly why ICS generation was moved out in the previous round.

### `static/js/app.js`

Loses the hard-coded element map for the five activities; reads the list from the new
module, sends `timezone` from `Intl.DateTimeFormat().resolvedOptions().timeZone`, and
sends `labels` from i18n.

### `static/js/i18n.js`

Two new keys (`shift`, `sleep`) for the ICS labels, plus the default activity names and
the new UI strings, in all four languages.

## Testing

TDD throughout: a failing test before each change.

Python:
- Validation bounds: bad `unit`, non-positive `amount`, over-long name, more than 20
  activities, duplicate ids, unknown timezone.
- Timezone actually applies: the same shift in two zones yields different local times.
- `find_free_slots` returns day indices.
- Prompt carries user activity names, ids and preferences.
- `parse_activity_plan` drops unknown ids and out-of-range indices.
- `generate_basic_plan` places inside the preferred window when it fits, and falls back
  when it does not.
- ICS summaries come from the request labels.

JavaScript (`node --test`):
- Defaults load on first run; a stored list wins over defaults.
- Add, rename, delete, and persistence round-trip.
- Payload building: ids unique, preferred defaults to `any`.

## Breaking change

`/generate-plan`'s contract changes and there is no compatibility shim. Frontend and
backend deploy together, so versioning the endpoint would be ceremony without a consumer.

The service worker cache must go to **v3** and `activities.js` must join the precache
list. A stale cache would serve an old `app.js` that posts the old body shape against the
new API — the same trap that made the v2 bump necessary last round.

`localStorage` uses a fresh key, so there is no old shape to migrate. Absent data means
the default template.
