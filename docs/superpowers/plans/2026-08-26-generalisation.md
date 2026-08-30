# Generalisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** complete — all tasks implemented on the `feat/user-defined-activities` branch (26 commits, 2026-08-26 → 28) and merged to `main` in PR #2 on 2026-08-30.

**Goal:** Turn ShiftScan from one person's planner into one anyone can use — user-defined activities, browser timezone, no Turkish strings in the backend.

**Architecture:** Configuration travels in each `POST /generate-plan` request; the backend stays stateless. The Gemini exchange moves from names to ids: the prompt lists activity ids, the model answers with `day_index` (0-6) and `activity_id`, and unknown values are dropped during validation. Translations live only in `static/js/i18n.js`.

**Tech Stack:** FastAPI, Pydantic v2, pytz, pytest; vanilla JS with `node --test`.

**Spec:** `docs/superpowers/specs/2026-08-26-generalisation-design.md`

## Global Constraints

- Python pins are exact (`==`) in `requirements.txt`; do not loosen them. Runtime target is Python 3.10 (Dockerfile base image).
- Day index 0 is Monday, matching the order of the `DAY_NAMES` list being deleted.
- `NIGHT_END_HOUR = 7` stays a module constant — a human rule, not a user setting.
- Preferred windows are constants: morning 06:00-12:00, afternoon 12:00-18:00, evening 18:00-23:00, `any` imposes nothing.
- `DEFAULT_SESSION_HOURS = 1.0` — one session's length when `unit` is `days`.
- Activity list limits: 1-20 entries, `id` 1-64 chars and unique, `name` 1-80 chars, `0 < amount <= 168`.
- Backend source files carry no Turkish user-facing strings once this plan is done. Turkish comments are fine.
- Every task ends with the full suite green: `.venv/bin/python -m pytest -q` and `node --test tests/js/*.test.js`.
- Commit after each task. Never commit with a failing suite.

---

### Task 1: Shared request models

**Files:**
- Create: `services/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing (new leaf module)
- Produces: `ActivityGoal(id: str, name: str, amount: float, unit: Literal["hours","days"], preferred: Literal["morning","afternoon","evening","any"])`, `CalendarLabels(shift: str, sleep: str)`, `MAX_ACTIVITIES: int`, `DEFAULT_SESSION_HOURS: float`, `PREFERRED_WINDOWS: dict[str, tuple[int, int]]`

- [x] **Step 1: Write the failing test**

```python
# tests/test_models.py
"""ActivityGoal ve CalendarLabels dogrulama sinirlari."""

import pytest
from pydantic import ValidationError

from services.models import (
    DEFAULT_SESSION_HOURS,
    MAX_ACTIVITIES,
    PREFERRED_WINDOWS,
    ActivityGoal,
    CalendarLabels,
)


def goal(**overrides):
    base = {"id": "a1", "name": "Sport", "amount": 3, "unit": "days"}
    base.update(overrides)
    return base


def test_preferred_defaults_to_any():
    assert ActivityGoal(**goal()).preferred == "any"


def test_unit_must_be_hours_or_days():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(unit="weeks"))


def test_amount_must_be_positive():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(amount=0))


def test_amount_cannot_exceed_a_full_week():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(amount=169))


def test_name_cannot_be_empty():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(name=""))


def test_name_length_is_bounded():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(name="x" * 81))


def test_preferred_must_be_a_known_window():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(preferred="midnight"))


def test_labels_have_neutral_defaults():
    labels = CalendarLabels()

    assert labels.shift == "Shift"
    assert labels.sleep == "Sleep"


def test_label_cannot_be_empty():
    with pytest.raises(ValidationError):
        CalendarLabels(shift="", sleep="Sleep")


def test_every_preferred_value_except_any_has_a_window():
    for value in ("morning", "afternoon", "evening"):
        start, end = PREFERRED_WINDOWS[value]
        assert 0 <= start < end <= 24

    assert "any" not in PREFERRED_WINDOWS


def test_module_constants_match_the_spec():
    assert MAX_ACTIVITIES == 20
    assert DEFAULT_SESSION_HOURS == 1.0
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_models.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.models'`

- [x] **Step 3: Write minimal implementation**

```python
# services/models.py
"""
Paylasilan istek modelleri.

Aktivite tanimlari ve takvim etiketleri istekle gelir; sunucu hicbir sey
saklamaz. Sinirlar burada tek yerde durur.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Bir istekte kabul edilen en fazla aktivite
MAX_ACTIVITIES = 20

# unit == "days" oldugunda tek bir oturumun uzunlugu
DEFAULT_SESSION_HOURS = 1.0

# Tercih edilen zaman pencereleri (yerel saat, [baslangic, bitis))
PREFERRED_WINDOWS = {
    "morning": (6, 12),
    "afternoon": (12, 18),
    "evening": (18, 23),
}


class ActivityGoal(BaseModel):
    """Kullanicinin tanimladigi tek bir haftalik aktivite hedefi."""

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    amount: float = Field(gt=0, le=168)
    unit: Literal["hours", "days"]
    preferred: Literal["morning", "afternoon", "evening", "any"] = "any"


class CalendarLabels(BaseModel):
    """ICS'te vardiya ve uyku bloklarinin adi; ceviri istemciden gelir."""

    shift: str = Field(default="Shift", min_length=1, max_length=80)
    sleep: str = Field(default="Sleep", min_length=1, max_length=80)
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_models.py -q`
Expected: PASS, 11 tests

- [x] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q && node --test tests/js/*.test.js`
Expected: all green (nothing else imports the new module yet)

- [x] **Step 6: Commit**

```bash
git add services/models.py tests/test_models.py
git commit -m "Add shared request models for user-defined activities"
```

---

### Task 2: ICS labels come from the request

**Files:**
- Modify: `services/ics_generator.py` (`generate_final_ics`)
- Modify: `main.py` (the `generate_final_ics` call)
- Test: `tests/test_ics_generator.py`

**Interfaces:**
- Consumes: `CalendarLabels` from Task 1
- Produces: `generate_final_ics(timeline, activity_events, labels: CalendarLabels) -> str`

- [x] **Step 1: Write the failing test**

Append to `tests/test_ics_generator.py`:

```python
def test_block_labels_come_from_the_request():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics(
        TIMELINE, [], CalendarLabels(shift="Schicht", sleep="Schlaf")
    )

    assert "SUMMARY:Schicht" in ics
    assert "SUMMARY:Schlaf" in ics
    assert "SUMMARY:Vardiya" not in ics


def test_labels_are_escaped_like_any_other_text():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics(TIMELINE, [], CalendarLabels(shift="Work, shift", sleep="Sleep"))

    assert "SUMMARY:Work\\, shift" in ics
```

Then update the existing `generate()` helper in that file so the other tests keep passing:

```python
def generate():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    return generate_final_ics(TIMELINE, ACTIVITIES, CalendarLabels(shift="Vardiya", sleep="Uyku"))
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ics_generator.py -q`
Expected: FAIL with `TypeError: generate_final_ics() takes 2 positional arguments but 3 were given`

- [x] **Step 3: Write minimal implementation**

In `services/ics_generator.py`, add the import and change the signature and the summary lookup:

```python
from services.models import CalendarLabels


def generate_final_ics(
    timeline: List[Tuple[datetime, datetime, str]],
    activity_events: List[Tuple[datetime, datetime, str]],
    labels: CalendarLabels
) -> str:
    stamp = datetime.now(timezone.utc)
    ics = generate_ics_header()

    for index, (start, end, block_type) in enumerate(timeline):
        summary = labels.shift if block_type == "shift" else labels.sleep
        uid = f"{block_type}-{start.strftime('%Y%m%d%H%M')}-{index}@shiftscan"
        ics += generate_ics_event(uid, start, end, summary, dtstamp=stamp)
```

The rest of the function is unchanged.

In `main.py`, pass labels through from the request. `PlanRequest` does not have the field yet, so add it in the same step:

```python
from services.models import CalendarLabels

class PlanRequest(BaseModel):
    start_date: str
    shift_text: str
    shift_events: List[ShiftEvent]
    activities: Dict[str, Activity]
    labels: CalendarLabels = CalendarLabels()
```

and at the call site:

```python
        final_ics = generate_final_ics(timeline, activity_events, plan_data.labels)
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ics_generator.py -q`
Expected: PASS

- [x] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q && node --test tests/js/*.test.js`
Expected: all green. `tests/test_api.py` still posts a body without `labels`, which is why the field has a default.

- [x] **Step 6: Commit**

```bash
git add services/ics_generator.py main.py tests/test_ics_generator.py
git commit -m "Take ICS block labels from the request instead of Turkish literals"
```

---

### Task 3: Timezone becomes a parameter

**Files:**
- Modify: `services/timeline_builder.py` (`build_timeline`, `find_free_slots`)
- Modify: `main.py` (`PlanRequest`, both call sites)
- Test: `tests/test_timeline_builder.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `build_timeline(shift_events, timezone: str)`, `find_free_slots(timeline, week_start, timezone: str)`. Both raise `pytz.UnknownTimeZoneError` for an unknown zone; Task 7 turns that into HTTP 400.

- [x] **Step 1: Write the failing test**

Append to `tests/test_timeline_builder.py`:

```python
def test_timezone_parameter_controls_local_time():
    """Ayni anlik zaman, farkli bolgede farkli yerel saate dusmeli."""
    events = [
        {
            "start": "2026-08-24T06:00:00Z",
            "end": "2026-08-24T15:00:00Z",
        }
    ]

    istanbul = build_timeline(events, "Europe/Istanbul")
    london = build_timeline(events, "Europe/London")

    istanbul_shift = next(s for s, _, kind in istanbul if kind == "shift")
    london_shift = next(s for s, _, kind in london if kind == "shift")

    assert istanbul_shift.hour == 9
    assert london_shift.hour == 7


def test_unknown_timezone_is_rejected():
    import pytz

    with pytest.raises(pytz.UnknownTimeZoneError):
        build_timeline([day_shift(24)], "Mars/Olympus")
```

Add `import pytest` to the top of the file, and update every existing `build_timeline(...)` and `find_free_slots(...)` call in that file to pass `"Europe/Istanbul"`.

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_timeline_builder.py -q`
Expected: FAIL with `TypeError: build_timeline() takes 1 positional argument but 2 were given`

- [x] **Step 3: Write minimal implementation**

In `services/timeline_builder.py`, replace both hard-coded lookups. In `build_timeline`:

```python
def build_timeline(
    shift_events: List[Dict], timezone: str
) -> List[Tuple[datetime, datetime, str]]:
    timeline = []
    istanbul_tz = pytz.timezone(timezone)
```

Rename the local variable from `istanbul_tz` to `local_tz` throughout both functions — the name is now a lie. In `find_free_slots`:

```python
def find_free_slots(
    timeline: List[Tuple[datetime, datetime, str]],
    week_start: date,
    timezone: str,
) -> List[Tuple[str, datetime, datetime]]:
    free_slots = []
    local_tz = pytz.timezone(timezone)
```

In `main.py`, add the field and thread it through:

```python
class PlanRequest(BaseModel):
    start_date: str
    timezone: str = "Europe/Istanbul"
    shift_text: str
    shift_events: List[ShiftEvent]
    activities: Dict[str, Activity]
    labels: CalendarLabels = CalendarLabels()
```

```python
        timeline = build_timeline(
            [event.model_dump() for event in plan_data.shift_events],
            plan_data.timezone,
        )
        free_slots = find_free_slots(timeline, week_start, plan_data.timezone)
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_timeline_builder.py -q`
Expected: PASS

- [x] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q && node --test tests/js/*.test.js`
Expected: all green

- [x] **Step 6: Commit**

```bash
git add services/timeline_builder.py main.py tests/test_timeline_builder.py
git commit -m "Make the timezone a parameter instead of a hard-coded literal"
```

---

### Task 4: Free slots carry a day index, not a Turkish name

**Files:**
- Modify: `services/timeline_builder.py` (delete `DAY_NAMES`, change return type)
- Modify: `services/ai_planner.py` (`create_gemini_activity_prompt`, `ActivityPlanItem`, `parse_activity_plan`, `apply_activity_plan`, `generate_basic_plan`)
- Test: `tests/test_timeline_builder.py`, `tests/test_ai_planner.py`

**Interfaces:**
- Consumes: `find_free_slots` from Task 3
- Produces: `find_free_slots(...) -> List[Tuple[int, datetime, datetime]]` where the int is 0-6 (Monday=0). `ActivityPlanItem(day_index: int, activity: str, hours: float)` — `activity` is still a name here; Task 5 turns it into an id.

- [x] **Step 1: Write the failing test**

Append to `tests/test_timeline_builder.py`:

```python
def test_free_slots_are_keyed_by_day_index():
    """Backend dil bagimsiz: gun adi degil 0-6 indeksi doner."""
    timeline = build_timeline([day_shift(24)], "Europe/Istanbul")

    slots = find_free_slots(timeline, WEEK_START, "Europe/Istanbul")

    indices = {day for day, _, _ in slots}
    assert indices <= set(range(7))
    assert 0 in indices  # Pazartesi
    assert all(isinstance(day, int) for day, _, _ in slots)
```

Replace the existing `days_with_slots` helper and its three callers so they compare indices:

```python
def days_with_slots(free_slots) -> set:
    return {day_index for day_index, _, _ in free_slots}
```

`test_day_without_shift_still_yields_a_free_slot` asserts `5 in ...` and `6 in ...`;
`test_week_follows_start_date_not_first_shift` asserts `== set(range(7))`;
the three tests that filter `if s[0] == "Salı"` / `"Çarşamba"` / `"Pazartesi"` filter on
`1`, `2` and `0`.

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_timeline_builder.py -q`
Expected: FAIL — `assert all(isinstance(day, int) ...)` fails because day names are strings

- [x] **Step 3: Write minimal implementation**

In `services/timeline_builder.py`, delete the `DAY_NAMES` constant and its docstring mention, and return the index:

```python
    for day_offset in range(7):
        current_day = week_start + timedelta(days=day_offset)
```

Remove the `day_name = DAY_NAMES[day_offset]` line and append `day_offset` instead:

```python
            if block_start > cursor:
                free_slots.append((day_offset, cursor, block_start))
```

Do the same for the trailing-slot append at the end of the loop body.

In `services/ai_planner.py`, the three consumers now receive indices. In
`create_gemini_activity_prompt`:

```python
    slot_summary = "FREE TIME (day index 0 = Monday):\n"
    day_totals = {}

    for day_index, start, end in free_slots:
        duration = (end - start).total_seconds() / 3600
        day_totals[day_index] = day_totals.get(day_index, 0) + duration

    for day_index in sorted(day_totals):
        slot_summary += f"- day {day_index}: {day_totals[day_index]:.1f} hours free\n"
```

In `ActivityPlanItem`, rename the field and bound it:

```python
class ActivityPlanItem(BaseModel):
    """Modelin dondurdugu tek bir plan satiri."""

    day_index: int = Field(ge=0, le=6)
    activity: str
    hours: float = Field(gt=0, le=MAX_ACTIVITY_HOURS)
```

In `apply_activity_plan`, match on the index:

```python
    available_slots = []
    for day_index, start, end in free_slots:
        available_slots.append({
            'day': day_index,
            'start': start,
            'end': end,
            'duration': (end - start).total_seconds() / 3600,
            'used_until': start
        })

    for plan_item in activity_plan:
        day = plan_item.day_index
```

In `generate_basic_plan`, the loop unpacks an index it does not use:

```python
        while remaining > 0 and slot_index < len(free_slots):
            _, start, end = free_slots[slot_index]
```

Update the JSON example at the end of the prompt to match the new field name:

```python
    prompt = f"""...
[
  {{"day_index": 0, "activity": "Spor", "hours": 1}}
]"""
```

Update `tests/test_ai_planner.py` wherever it constructs `ActivityPlanItem(day=...)` or a
raw dict with `"day"` so it uses `day_index` with an integer, and wherever it passes
`free_slots` so the first element is an int.

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS

- [x] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q && node --test tests/js/*.test.js`
Expected: all green

- [x] **Step 6: Commit**

```bash
git add services/timeline_builder.py services/ai_planner.py tests/
git commit -m "Return day indices from the planner instead of Turkish day names"
```

---

### Task 5: Activities become user-defined

**Files:**
- Modify: `services/ai_planner.py` (delete `ACTIVITY_MAP`, rewrite prompt, `parse_activity_plan`, `apply_activity_plan`, `generate_basic_plan`)
- Modify: `main.py` (`PlanRequest.activities`, delete the `Activity` model)
- Test: `tests/test_ai_planner.py`

**Interfaces:**
- Consumes: `ActivityGoal` from Task 1, day indices from Task 4
- Produces: `create_gemini_activity_prompt(free_slots, goals: List[ActivityGoal]) -> str`; `ActivityPlanItem(day_index: int, activity_id: str, hours: float)`; `parse_activity_plan(raw, known_ids: set[str]) -> List[ActivityPlanItem]`; `apply_activity_plan(free_slots, activity_plan, goals) -> List[Tuple[datetime, datetime, str]]`; `generate_basic_plan(free_slots, goals) -> List[Tuple[datetime, datetime, str]]`

- [x] **Step 1: Write the failing test**

Create `tests/test_activity_goals.py`:

```python
"""Kullanici tanimli aktivitelerin prompt, dogrulama ve yerlestirmedeki davranisi."""

from datetime import datetime, timedelta

import pytz

from services.ai_planner import (
    ActivityPlanItem,
    apply_activity_plan,
    create_gemini_activity_prompt,
    generate_basic_plan,
    parse_activity_plan,
)
from services.models import ActivityGoal

IST = pytz.timezone("Europe/Istanbul")


def slot(day_index: int, start_hour: int, end_hour: int):
    day = 24 + day_index
    return (
        day_index,
        IST.localize(datetime(2026, 8, day, start_hour)),
        IST.localize(datetime(2026, 8, day, end_hour)),
    )


GOALS = [
    ActivityGoal(id="a1", name="Guitar practice", amount=2, unit="hours", preferred="evening"),
    ActivityGoal(id="a2", name="Sport", amount=2, unit="days", preferred="morning"),
]


def test_prompt_lists_user_activity_names_and_ids():
    prompt = create_gemini_activity_prompt([slot(0, 7, 23)], GOALS)

    assert "a1" in prompt
    assert "Guitar practice" in prompt
    assert "a2" in prompt
    assert "Sport" in prompt


def test_prompt_states_the_preferred_window():
    prompt = create_gemini_activity_prompt([slot(0, 7, 23)], GOALS)

    assert "evening" in prompt
    assert "morning" in prompt


def test_prompt_carries_no_hard_coded_activity_rules():
    prompt = create_gemini_activity_prompt([slot(0, 7, 23)], GOALS)

    assert "Kitap Okuma" not in prompt
    assert "İçerik Üretimi" not in prompt


def test_prompt_asks_for_ids_not_names():
    prompt = create_gemini_activity_prompt([slot(0, 7, 23)], GOALS)

    assert "activity_id" in prompt
    assert "day_index" in prompt


def test_unknown_activity_id_is_dropped():
    raw = [
        {"day_index": 0, "activity_id": "a1", "hours": 1},
        {"day_index": 0, "activity_id": "ghost", "hours": 1},
    ]

    parsed = parse_activity_plan(raw, {"a1", "a2"})

    assert [item.activity_id for item in parsed] == ["a1"]


def test_day_index_out_of_range_is_dropped():
    raw = [{"day_index": 9, "activity_id": "a1", "hours": 1}]

    assert parse_activity_plan(raw, {"a1"}) == []


def test_applied_events_use_the_user_supplied_name():
    plan = [ActivityPlanItem(day_index=0, activity_id="a1", hours=1)]

    events = apply_activity_plan([slot(0, 18, 22)], plan, GOALS)

    assert [name for _, _, name in events] == ["Guitar practice"]


def test_basic_plan_prefers_the_requested_window():
    goals = [ActivityGoal(id="a1", name="Reading", amount=1, unit="hours", preferred="evening")]
    slots = [slot(0, 7, 10), slot(0, 19, 22)]

    events = generate_basic_plan(slots, goals)

    assert events
    start, _, _ = events[0]
    assert start.hour >= 18


def test_basic_plan_falls_back_when_the_window_has_no_room():
    goals = [ActivityGoal(id="a1", name="Reading", amount=1, unit="hours", preferred="evening")]
    slots = [slot(0, 7, 10)]  # sabah disinda bos zaman yok

    events = generate_basic_plan(slots, goals)

    assert len(events) == 1
    start, _, _ = events[0]
    assert start.hour == 7


def test_days_unit_uses_the_default_session_length():
    from services.models import DEFAULT_SESSION_HOURS

    goals = [ActivityGoal(id="a1", name="Sport", amount=2, unit="days", preferred="any")]
    slots = [slot(0, 7, 23), slot(1, 7, 23)]

    events = generate_basic_plan(slots, goals)

    total = sum((end - start).total_seconds() / 3600 for start, end, _ in events)
    assert total == 2 * DEFAULT_SESSION_HOURS
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_activity_goals.py -q`
Expected: FAIL — `TypeError` on `parse_activity_plan()` taking one argument, and `ActivityPlanItem` having no `activity_id`

- [x] **Step 3: Write minimal implementation**

In `services/ai_planner.py`, delete `ACTIVITY_MAP` entirely and import the shared models:

```python
from services.models import DEFAULT_SESSION_HOURS, PREFERRED_WINDOWS, ActivityGoal
```

Rewrite the prompt builder:

```python
def create_gemini_activity_prompt(
    free_slots: List[Tuple[int, datetime, datetime]],
    goals: List[ActivityGoal]
) -> str:
    """Kullanicinin tanimladigi hedeflerden dil bagimsiz bir prompt uretir."""
    slot_summary = "FREE TIME (day index 0 = Monday):\n"
    day_totals = {}

    for day_index, start, end in free_slots:
        duration = (end - start).total_seconds() / 3600
        day_totals[day_index] = day_totals.get(day_index, 0) + duration

    for day_index in sorted(day_totals):
        slot_summary += f"- day {day_index}: {day_totals[day_index]:.1f} hours free\n"

    activity_goals = "ACTIVITY GOALS:\n"
    for goal in goals:
        if goal.unit == "days":
            amount = f"{goal.amount:g} days per week, {DEFAULT_SESSION_HOURS:g} hour each"
        else:
            amount = f"{goal.amount:g} hours per week"

        if goal.preferred == "any":
            window = "no time preference"
        else:
            start_hour, end_hour = PREFERRED_WINDOWS[goal.preferred]
            window = f"prefer {goal.preferred} ({start_hour:02d}:00-{end_hour:02d}:00)"

        activity_goals += f'- id {goal.id} "{goal.name}": {amount}, {window}\n'

    return f"""You are a scheduling assistant. Distribute the activities below across the free time.

{slot_summary}
{activity_goals}
RULES:
- Do not overlap activities.
- Keep activities in waking hours; avoid 01:00-06:00.
- Respect each activity's preferred window when the free time allows it.
- Do not schedule demanding activities right after a shift ends.

Return ONLY JSON, no other text. Use the activity ids above, never the names:
[
  {{"day_index": 0, "activity_id": "a1", "hours": 1}}
]"""
```

Change the plan item and its validation:

```python
class ActivityPlanItem(BaseModel):
    """Modelin dondurdugu tek bir plan satiri."""

    day_index: int = Field(ge=0, le=6)
    activity_id: str
    hours: float = Field(gt=0, le=MAX_ACTIVITY_HOURS)
```

```python
def parse_activity_plan(raw: Any, known_ids: set) -> List[ActivityPlanItem]:
    """
    Dil modelinden gelen ham plan ciktisini dogrular.

    Model ciktisi guvenilmez: alan eksik olabilir, sayi string gelebilir,
    liste yerine dict donebilir, uydurma bir aktivite id'si gelebilir.
    Gecerli satirlar korunur, gecersizler atlanir; exception yukselmez.
    """
    if not isinstance(raw, list):
        return []

    items = []
    for entry in raw:
        try:
            item = ActivityPlanItem.model_validate(entry)
        except ValidationError:
            continue

        if item.activity_id not in known_ids:
            continue

        items.append(item)

    return items
```

Keep whatever the current body does for the non-list case and the per-row `try`; the only
additions are the `known_ids` check and the renamed fields.

`apply_activity_plan` gains the goals and resolves names from them:

```python
def apply_activity_plan(
    free_slots: List[Tuple[int, datetime, datetime]],
    activity_plan: List[ActivityPlanItem],
    goals: List[ActivityGoal]
) -> List[Tuple[datetime, datetime, str]]:
    names = {goal.id: goal.name for goal in goals}
    activity_events = []

    available_slots = []
    for day_index, start, end in free_slots:
        available_slots.append({
            'day': day_index,
            'start': start,
            'end': end,
            'duration': (end - start).total_seconds() / 3600,
            'used_until': start
        })

    for plan_item in activity_plan:
        activity_name = names.get(plan_item.activity_id)
        if not activity_name:
            continue

        day = plan_item.day_index
        hours_needed = plan_item.hours
```

The rest of the placement loop is unchanged.

`generate_basic_plan` takes goals and honours the preferred window:

```python
def generate_basic_plan(
    free_slots: List[Tuple[int, datetime, datetime]],
    goals: List[ActivityGoal]
) -> List[Tuple[datetime, datetime, str]]:
    """
    API olmadan basit aktivite plani olusturur (fallback).

    Tercih edilen pencereye denk gelen slotlar once denenir; aktivite oraya
    sigmazsa herhangi bir bos slota konur. Yerlesemeyen saatler sessizce
    dusulur - kullaniciya bildirmek backlog madde 8.
    """
    activity_events = []
    used_until = {index: start for index, (_, start, _) in enumerate(free_slots)}

    def slot_matches(slot_index: int, preferred: str) -> bool:
        if preferred == "any":
            return True
        window_start, window_end = PREFERRED_WINDOWS[preferred]
        _, start, end = free_slots[slot_index]
        return start.hour < window_end and end.hour > window_start

    for goal in goals:
        if goal.unit == "days":
            remaining = goal.amount * DEFAULT_SESSION_HOURS
        else:
            remaining = goal.amount

        preferred_order = [i for i in range(len(free_slots)) if slot_matches(i, goal.preferred)]
        fallback_order = [i for i in range(len(free_slots)) if i not in preferred_order]

        for slot_index in preferred_order + fallback_order:
            if remaining <= 0:
                break

            _, slot_start, slot_end = free_slots[slot_index]
            cursor = used_until[slot_index]
            available = (slot_end - cursor).total_seconds() / 3600
            if available <= 0:
                continue

            hours_to_use = min(remaining, available, 2)
            activity_end = cursor + timedelta(hours=hours_to_use)
            activity_events.append((cursor, activity_end, goal.name))
            used_until[slot_index] = activity_end
            remaining -= hours_to_use

    return activity_events
```

In `main.py`, delete the `Activity` model and switch the field to a list:

```python
from services.models import ActivityGoal, CalendarLabels

class PlanRequest(BaseModel):
    start_date: str
    timezone: str = "Europe/Istanbul"
    shift_text: str
    shift_events: List[ShiftEvent]
    activities: List[ActivityGoal]
    labels: CalendarLabels = CalendarLabels()
```

and update the two calls plus the id set:

```python
        known_ids = {goal.id for goal in plan_data.activities}
        activity_plan = await get_gemini_activity_plan(
            free_slots, plan_data.activities, known_ids, timeout=GEMINI_TIMEOUT_SECONDS
        )

        if activity_plan:
            activity_events = apply_activity_plan(
                free_slots, activity_plan, plan_data.activities
            )
            plan_source = "ai"
        else:
            activity_events = generate_basic_plan(free_slots, plan_data.activities)
            plan_source = "fallback"
```

`get_gemini_activity_plan` gains the same parameter and forwards it to
`parse_activity_plan`:

```python
async def get_gemini_activity_plan(
    free_slots: List[Tuple[int, datetime, datetime]],
    goals: List[ActivityGoal],
    known_ids: set,
    timeout: float = 30.0,
) -> List[ActivityPlanItem]:
```

Update `tests/test_ai_planner.py` and `tests/test_api.py` to the new shapes: activities are
a list of dicts with `id`/`name`/`amount`/`unit`, `parse_activity_plan` takes a second
argument, and `apply_activity_plan` takes a third.

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS

- [x] **Step 5: Verify no Turkish user-facing strings remain in the planner**

Run: `grep -nE "Vardiya|Uyku|Spor|Kitap|Sosyal|Oyun|İçerik" services/*.py`
Expected: no matches

- [x] **Step 6: Commit**

```bash
git add services/ai_planner.py main.py tests/
git commit -m "Replace the fixed activity map with user-defined activity goals"
```

---

### Task 6: Request hardening and dead field removal

**Files:**
- Modify: `main.py` (timezone validation, activity list limits, remove unused fields)
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `PlanRequest` from Task 5
- Produces: `POST /generate-plan` returns 400 for an unknown timezone, 422 for a list outside 1-20 or duplicate ids

- [x] **Step 1: Write the failing test**

Append to `tests/test_api.py` (reuse whatever client fixture the file already defines):

```python
def test_unknown_timezone_returns_400(client):
    response = client.post("/generate-plan", json=plan_body(timezone="Mars/Olympus"))

    assert response.status_code == 400
    assert "timezone" in response.json()["detail"].lower()


def test_empty_activity_list_is_rejected(client):
    response = client.post("/generate-plan", json=plan_body(activities=[]))

    assert response.status_code == 422


def test_too_many_activities_are_rejected(client):
    many = [
        {"id": f"a{i}", "name": f"Activity {i}", "amount": 1, "unit": "hours"}
        for i in range(21)
    ]

    response = client.post("/generate-plan", json=plan_body(activities=many))

    assert response.status_code == 422


def test_duplicate_activity_ids_are_rejected(client):
    duplicated = [
        {"id": "a1", "name": "One", "amount": 1, "unit": "hours"},
        {"id": "a1", "name": "Two", "amount": 1, "unit": "hours"},
    ]

    response = client.post("/generate-plan", json=plan_body(activities=duplicated))

    assert response.status_code == 422
```

Add the helper near the top of the file:

```python
def plan_body(**overrides):
    body = {
        "start_date": "2026-08-24",
        "timezone": "Europe/Istanbul",
        "shift_events": [
            {"start": "2026-08-24T09:00:00+03:00", "end": "2026-08-24T18:00:00+03:00"}
        ],
        "activities": [
            {"id": "a1", "name": "Reading", "amount": 2, "unit": "hours"}
        ],
        "labels": {"shift": "Shift", "sleep": "Sleep"},
    }
    body.update(overrides)
    return body
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_api.py -q`
Expected: FAIL — the unknown timezone raises `UnknownTimeZoneError` and surfaces as 500, and the list limits do not exist

- [x] **Step 3: Write minimal implementation**

In `main.py`, drop the unused fields and add the constraints:

```python
class ShiftEvent(BaseModel):
    start: str
    end: str


class PlanRequest(BaseModel):
    start_date: str
    timezone: str = "Europe/Istanbul"
    shift_events: List[ShiftEvent]
    activities: List[ActivityGoal] = Field(min_length=1, max_length=MAX_ACTIVITIES)
    labels: CalendarLabels = CalendarLabels()

    @field_validator("activities")
    @classmethod
    def ids_must_be_unique(cls, goals: List[ActivityGoal]) -> List[ActivityGoal]:
        ids = [goal.id for goal in goals]
        if len(set(ids)) != len(ids):
            raise ValueError("activity ids must be unique")
        return goals
```

Import what this needs:

```python
from pydantic import BaseModel, Field, field_validator
from services.models import MAX_ACTIVITIES, ActivityGoal, CalendarLabels
```

Validate the timezone before using it:

```python
def _validate_timezone(name: str) -> str:
    """Bilinmeyen bolge 500 yerine 400 olarak donmeli."""
    try:
        pytz.timezone(name)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail=f"Unknown timezone: {name}")
    return name
```

and call it at the top of `generate_plan`, before `build_timeline`:

```python
        timezone = _validate_timezone(plan_data.timezone)
```

then pass `timezone` instead of `plan_data.timezone` to both calls. Add `import pytz` if
`main.py` does not already have it.

Note: `generate_plan` already opens with `except HTTPException: raise` before its generic
handler, so a 400 raised by `_validate_timezone` inside the `try` block propagates
untouched. Do not modify the exception handling — the generic branch deliberately logs the
full trace via `traceback.print_exc()` and returns a fixed message so nothing leaks to the
client. `tests/test_api.py` guards this.

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_api.py -q`
Expected: PASS

- [x] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q && node --test tests/js/*.test.js`
Expected: all green

- [x] **Step 6: Commit**

```bash
git add main.py tests/test_api.py
git commit -m "Validate the timezone and bound the activity list"
```

---

### Task 7: Activity list module in the browser

**Files:**
- Create: `static/js/activities.js`
- Test: `tests/js/activities.test.js`

**Interfaces:**
- Consumes: nothing (leaf module, same export shape as `static/js/ics.js`)
- Produces: `window.ShiftScanActivities` / `module.exports` with `defaultActivities(names)`, `load(storage, names)`, `save(storage, list)`, `addActivity(list, entry)`, `removeActivity(list, id)`, `toPayload(list)`, `STORAGE_KEY`

- [x] **Step 1: Write the failing test**

```javascript
// tests/js/activities.test.js
const test = require('node:test');
const assert = require('node:assert');
const A = require('../../static/js/activities.js');

const NAMES = {
    'content-production': 'Content',
    sports: 'Sports',
    reading: 'Reading',
    social: 'Social',
    gaming: 'Gaming'
};

function fakeStorage(initial) {
    const data = { ...initial };
    return {
        getItem: (k) => (k in data ? data[k] : null),
        setItem: (k, v) => { data[k] = String(v); },
        _data: data
    };
}

test('defaults are named from the supplied translations', () => {
    const list = A.defaultActivities(NAMES);
    assert.deepStrictEqual(list.map((a) => a.name), Object.values(NAMES));
});

test('defaults have unique ids', () => {
    const ids = A.defaultActivities(NAMES).map((a) => a.id);
    assert.strictEqual(new Set(ids).size, ids.length);
});

test('load returns defaults when storage is empty', () => {
    const list = A.load(fakeStorage({}), NAMES);
    assert.strictEqual(list.length, Object.keys(NAMES).length);
});

test('a stored list wins over the defaults', () => {
    const stored = [{ id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'evening' }];
    const storage = fakeStorage({ [A.STORAGE_KEY]: JSON.stringify(stored) });

    assert.deepStrictEqual(A.load(storage, NAMES), stored);
});

test('corrupt stored data falls back to defaults instead of throwing', () => {
    const storage = fakeStorage({ [A.STORAGE_KEY]: 'not json' });
    assert.strictEqual(A.load(storage, NAMES).length, Object.keys(NAMES).length);
});

test('save round-trips through storage', () => {
    const storage = fakeStorage({});
    const list = [{ id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'any' }];

    A.save(storage, list);

    assert.deepStrictEqual(A.load(storage, NAMES), list);
});

test('added activities get an id that does not collide', () => {
    const list = A.defaultActivities(NAMES);
    const grown = A.addActivity(list, { name: 'Guitar', amount: 2, unit: 'hours' });

    const ids = grown.map((a) => a.id);
    assert.strictEqual(new Set(ids).size, ids.length);
    assert.strictEqual(grown.length, list.length + 1);
});

test('a new activity defaults to no time preference', () => {
    const grown = A.addActivity([], { name: 'Guitar', amount: 2, unit: 'hours' });
    assert.strictEqual(grown[0].preferred, 'any');
});

test('removing an activity leaves the others untouched', () => {
    const list = A.defaultActivities(NAMES);
    const shrunk = A.removeActivity(list, list[1].id);

    assert.strictEqual(shrunk.length, list.length - 1);
    assert.ok(!shrunk.some((a) => a.id === list[1].id));
});

test('payload carries only the fields the API accepts', () => {
    const list = [{ id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'evening', enabled: true }];

    assert.deepStrictEqual(A.toPayload(list), [
        { id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'evening' }
    ]);
});

test('disabled activities are left out of the payload', () => {
    const list = [
        { id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'any', enabled: false },
        { id: 'x2', name: 'Sport', amount: 1, unit: 'days', preferred: 'any', enabled: true }
    ];

    assert.deepStrictEqual(A.toPayload(list).map((a) => a.id), ['x2']);
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `node --test tests/js/activities.test.js`
Expected: FAIL with `Cannot find module '../../static/js/activities.js'`

- [x] **Step 3: Write minimal implementation**

```javascript
// static/js/activities.js
/**
 * ShiftScan - kullanici tanimli aktivite listesi
 * Hem tarayicida (window.ShiftScanActivities) hem Node'da (require) calisir.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.ShiftScanActivities = api;
    }
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const STORAGE_KEY = 'shiftscan-activities-v1';

    // Varsayilan sablon: eskiden sabit kodlanmis bes aktivite, artik
    // duzenlenebilir siradan satirlar.
    const DEFAULT_TEMPLATE = [
        { key: 'content-production', amount: 4, unit: 'hours', preferred: 'afternoon' },
        { key: 'sports', amount: 3, unit: 'days', preferred: 'morning' },
        { key: 'reading', amount: 5, unit: 'hours', preferred: 'evening' },
        { key: 'social', amount: 4, unit: 'hours', preferred: 'evening' },
        { key: 'gaming', amount: 2, unit: 'hours', preferred: 'any' }
    ];

    function defaultActivities(names) {
        return DEFAULT_TEMPLATE.map(function (entry, index) {
            return {
                id: 'd' + (index + 1),
                name: (names && names[entry.key]) || entry.key,
                amount: entry.amount,
                unit: entry.unit,
                preferred: entry.preferred,
                enabled: true
            };
        });
    }

    function load(storage, names) {
        try {
            const raw = storage.getItem(STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed) && parsed.length) return parsed;
            }
        } catch (err) {
            // Bozuk veya erisilemeyen depolama varsayilanlari engellememeli
        }
        return defaultActivities(names);
    }

    function save(storage, list) {
        try {
            storage.setItem(STORAGE_KEY, JSON.stringify(list));
        } catch (err) {
            // Depolama dolu veya kapali olabilir; plan uretimi yine calisir
        }
    }

    function nextId(list) {
        let candidate = 1;
        const taken = new Set(list.map(function (a) { return a.id; }));
        while (taken.has('u' + candidate)) candidate += 1;
        return 'u' + candidate;
    }

    function addActivity(list, entry) {
        return list.concat([{
            id: nextId(list),
            name: entry.name,
            amount: entry.amount,
            unit: entry.unit,
            preferred: entry.preferred || 'any',
            enabled: true
        }]);
    }

    function removeActivity(list, id) {
        return list.filter(function (a) { return a.id !== id; });
    }

    function toPayload(list) {
        return list
            .filter(function (a) { return a.enabled !== false; })
            .map(function (a) {
                return {
                    id: a.id,
                    name: a.name,
                    amount: a.amount,
                    unit: a.unit,
                    preferred: a.preferred || 'any'
                };
            });
    }

    return {
        STORAGE_KEY: STORAGE_KEY,
        defaultActivities: defaultActivities,
        load: load,
        save: save,
        addActivity: addActivity,
        removeActivity: removeActivity,
        toPayload: toPayload
    };
});
```

- [x] **Step 4: Run test to verify it passes**

Run: `node --test tests/js/activities.test.js`
Expected: PASS, 11 tests

- [x] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q && node --test tests/js/*.test.js`
Expected: all green

- [x] **Step 6: Commit**

```bash
git add static/js/activities.js tests/js/activities.test.js
git commit -m "Add a testable activity list module for the browser"
```

---

### Task 8: Wire the frontend to the new contract

**Files:**
- Modify: `templates/index.html` (replace the five activity blocks, add the script tag)
- Modify: `static/js/app.js` (element map, payload building)
- Modify: `static/js/i18n.js` (new keys in four languages)
- Modify: `static/sw.js` (cache v3, precache `activities.js`)

**Interfaces:**
- Consumes: `window.ShiftScanActivities` from Task 7
- Produces: a request body matching the contract in Task 6

- [x] **Step 1: Replace the activity markup**

In `templates/index.html`, delete the five `<div>` blocks holding `content-production`,
`sports`, `reading`, `social` and `gaming` (they sit between the activities heading and the
end of that section), and put this in their place:

```html
<ul id="activity-list" class="activity-list"></ul>
<button type="button" id="add-activity" class="btn btn-secondary" data-i18n="addActivity">
  + Aktivite Ekle
</button>

<template id="activity-row-template">
  <li class="activity-row">
    <input type="checkbox" class="checkbox activity-enabled" checked />
    <input type="text" class="input activity-name" maxlength="80" />
    <input type="number" class="input activity-amount" min="1" max="168" step="1" />
    <select class="select activity-unit">
      <option value="hours" data-i18n="unitHours">saat</option>
      <option value="days" data-i18n="unitDays">gün</option>
    </select>
    <select class="select activity-preferred">
      <option value="any" data-i18n="preferAny">Fark etmez</option>
      <option value="morning" data-i18n="preferMorning">Sabah</option>
      <option value="afternoon" data-i18n="preferAfternoon">Öğlen</option>
      <option value="evening" data-i18n="preferEvening">Akşam</option>
    </select>
    <button type="button" class="btn-icon activity-remove" aria-label="Sil">✕</button>
  </li>
</template>
```

Add the script tag before `app.js`, next to the existing `ics.js` line:

```html
    <script src="/static/js/activities.js"></script>
```

- [x] **Step 2: Add the translation keys**

In `static/js/i18n.js`, add these keys to all four language blocks (`tr`, `en`, `de`, `fr`).
Turkish shown; translate the rest in kind:

```javascript
            // Aktiviteler
            addActivity: '+ Aktivite Ekle',
            unitHours: 'saat',
            unitDays: 'gün',
            preferAny: 'Fark etmez',
            preferMorning: 'Sabah',
            preferAfternoon: 'Öğlen',
            preferEvening: 'Akşam',
            // ICS etiketleri
            icsShift: 'Vardiya',
            icsSleep: 'Uyku',
            // Varsayilan aktivite adlari
            'content-production': 'İçerik Üretimi',
            sports: 'Spor',
            reading: 'Kitap Okuma',
            social: 'Sosyal Yaşam',
            gaming: 'Oyun / Dinlenme',
```

- [x] **Step 3: Rewrite the activity handling in app.js**

Delete the `elements` entries for the five fixed activities and the code that reads them.
Replace with list rendering and payload building:

```javascript
    // ============================================
    // AKTİVİTE LİSTESİ
    // ============================================

    const activityListEl = document.getElementById('activity-list');
    const activityTemplate = document.getElementById('activity-row-template');
    let activities = ShiftScanActivities.load(localStorage, activityNames());

    function activityNames() {
        const keys = ['content-production', 'sports', 'reading', 'social', 'gaming'];
        const names = {};
        keys.forEach((key) => { names[key] = window.i18n ? window.i18n.t(key) : key; });
        return names;
    }

    function persist() {
        ShiftScanActivities.save(localStorage, activities);
    }

    function renderActivities() {
        activityListEl.innerHTML = '';

        activities.forEach((activity) => {
            const row = activityTemplate.content.cloneNode(true);
            const li = row.querySelector('.activity-row');

            const enabled = li.querySelector('.activity-enabled');
            const name = li.querySelector('.activity-name');
            const amount = li.querySelector('.activity-amount');
            const unit = li.querySelector('.activity-unit');
            const preferred = li.querySelector('.activity-preferred');

            enabled.checked = activity.enabled !== false;
            name.value = activity.name;
            amount.value = activity.amount;
            unit.value = activity.unit;
            preferred.value = activity.preferred || 'any';

            enabled.addEventListener('change', () => {
                activity.enabled = enabled.checked;
                persist();
            });
            name.addEventListener('input', () => { activity.name = name.value; persist(); });
            amount.addEventListener('input', () => {
                activity.amount = Number(amount.value);
                persist();
            });
            unit.addEventListener('change', () => { activity.unit = unit.value; persist(); });
            preferred.addEventListener('change', () => {
                activity.preferred = preferred.value;
                persist();
            });
            li.querySelector('.activity-remove').addEventListener('click', () => {
                activities = ShiftScanActivities.removeActivity(activities, activity.id);
                persist();
                renderActivities();
            });

            activityListEl.appendChild(row);
        });
    }

    document.getElementById('add-activity').addEventListener('click', () => {
        activities = ShiftScanActivities.addActivity(activities, {
            name: window.i18n ? window.i18n.t('addActivity') : 'Activity',
            amount: 1,
            unit: 'hours'
        });
        persist();
        renderActivities();
    });

    renderActivities();
```

Then change the request body where `/generate-plan` is called. Find the existing `fetch`
to `/generate-plan` and replace its `body` with:

```javascript
            body: JSON.stringify({
                start_date: startDate,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                shift_events: shiftEvents.map((ev) => ({
                    start: ev.start.toISOString(),
                    end: ev.end.toISOString()
                })),
                activities: ShiftScanActivities.toPayload(activities),
                labels: {
                    shift: window.i18n ? window.i18n.t('icsShift') : 'Shift',
                    sleep: window.i18n ? window.i18n.t('icsSleep') : 'Sleep'
                }
            })
```

`shift_text` is no longer sent — the backend dropped it in Task 6.

- [x] **Step 4: Bump the service worker**

In `static/sw.js`:

```javascript
const CACHE_NAME = 'vardiya-takvimi-v3';
const STATIC_CACHE = 'vardiya-static-v3';
```

and add the new file to `STATIC_ASSETS`, next to `ics.js`:

```javascript
    '/static/js/activities.js',
```

Without this bump a cached `app.js` posts the old body shape at the new API.

- [x] **Step 5: Verify**

Run: `.venv/bin/python -m pytest -q && node --test tests/js/*.test.js`
Expected: all green

Run: `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('ok')"`
Expected: `ok` (syntax check — `app.js` itself has no unit tests)

Then start the app and click through it:

```bash
.venv/bin/python -m uvicorn main:app --port 8000
```

Check by hand: the default five activities render; adding, renaming and deleting works;
a reload keeps the list; generating a plan returns an ICS whose SUMMARY lines use the
labels of the currently selected language.

- [x] **Step 6: Commit**

```bash
git add templates/index.html static/js/app.js static/js/i18n.js static/sw.js
git commit -m "Wire the frontend to user-defined activities and browser timezone"
```

---

### Task 9: Documentation

**Files:**
- Modify: `README.md`, `README_TR.md`

**Interfaces:**
- Consumes: the finished behaviour from Tasks 1-8
- Produces: nothing code-facing

- [x] **Step 1: Update both READMEs**

Add a section describing user-defined activities, and correct anything that describes the
old fixed five. State that the activity list lives in the browser's `localStorage` and is
never sent anywhere except as part of a plan request — this matters because the privacy
section already promises the app stores nothing server-side.

- [x] **Step 2: Verify the claims**

Run: `grep -niE "aktivite|activity" README.md README_TR.md`
Read each hit and confirm it matches what the app now does.

- [x] **Step 3: Commit**

```bash
git add README.md README_TR.md
git commit -m "Document user-defined activities"
```

---

## Notes for the executor

- The suite must be green at the end of every task. If a task leaves it red, the task
  boundary was wrong — say so rather than pushing on.
- `tests/test_api.py` contains a test asserting that error responses do not leak internals
  (`SECRET_ERROR`). Do not weaken it while touching the exception handling in Task 6.
- Docker cannot be built on the dev machine. CI covers it; do not claim a Docker change
  is verified locally.
