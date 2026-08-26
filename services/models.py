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
