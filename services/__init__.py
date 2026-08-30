"""
ShiftScan - Services Package
Backend servis modulleri
"""

from .timeline_builder import build_timeline, find_free_slots, DAY_NAMES

from .ics_generator import (
    generate_ics_header,
    generate_ics_event,
    generate_final_ics,
)

from .ai_planner import (
    ActivityPlanItem,
    parse_activity_plan,
    is_gemini_configured,
    configure_gemini,
    create_gemini_activity_prompt,
    get_gemini_activity_plan,
    apply_activity_plan,
    generate_basic_plan,
    ACTIVITY_MAP,
)

__all__ = [
    # timeline_builder
    'build_timeline',
    'find_free_slots',
    'DAY_NAMES',

    # ics_generator
    'generate_ics_header',
    'generate_ics_event',
    'generate_final_ics',

    # ai_planner
    'ActivityPlanItem',
    'parse_activity_plan',
    'is_gemini_configured',
    'configure_gemini',
    'create_gemini_activity_prompt',
    'get_gemini_activity_plan',
    'apply_activity_plan',
    'generate_basic_plan',
    'ACTIVITY_MAP',
]
