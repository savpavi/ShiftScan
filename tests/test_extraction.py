"""Görsel çıkarımı: bilinmeyen günleri izin sayma, kişi/gün bağını koru."""
import base64
from datetime import date
import pytest
from pydantic import ValidationError
from services.schedule_extraction import normalize_schedule, validate_image

WEEK = date(2026, 9, 7)

def test_missing_days_remain_unknown_and_people_are_separate():
    raw = {'people': [
        {'id': 'a', 'name': 'A', 'days': [{'day_index': 2, 'status': 'work', 'shifts': [{'start': '22:00', 'end': '06:00'}]}]},
        {'id': 'b', 'name': 'B', 'days': [{'day_index': 2, 'status': 'off'}]},
    ]}
    result = normalize_schedule(raw, WEEK)
    assert len(result['people']) == 2
    assert result['people'][0]['days'][0]['status'] == 'unknown'
    assert result['people'][0]['days'][2]['shifts'] == [{'start': '22:00', 'end': '06:00'}]
    assert result['people'][1]['days'][2]['status'] == 'off'
    assert result['people'][0]['days'][2]['date'] == '2026-09-09'

def test_date_overrules_disagreeing_day_and_requires_review():
    result = normalize_schedule({'people': [{'id':'a','name':'A','days':[
        {'date':'2026-09-10','day_index':0,'status':'off'}]}]}, WEEK)
    assert result['people'][0]['days'][3]['issue']
    assert result['people'][0]['days'][0]['status'] == 'unknown'

def test_outside_week_does_not_silently_reassign():
    result = normalize_schedule({'people':[{'id':'a','name':'A','days':[
        {'date':'2026-10-01','day_index':0,'status':'off'}]}]}, WEEK)
    assert all(d['status'] == 'unknown' for d in result['people'][0]['days'])
    assert result['warnings']

def test_duplicate_days_are_not_silently_overwritten():
    result = normalize_schedule({'people':[{'id':'a','name':'A','days':[
        {'day_index':0,'status':'off'},
        {'day_index':0,'status':'work','shifts':[{'start':'09:00','end':'18:00'}]}]}]}, WEEK)
    assert result['people'][0]['days'][0]['status'] == 'unknown'
    assert result['people'][0]['days'][0]['issue']

@pytest.mark.parametrize('shift',[{'start':'29:00','end':'18:00'}, {'start':'09:00','end':'09:00'}])
def test_invalid_hours_rejected(shift):
    with pytest.raises((ValueError,ValidationError)):
        normalize_schedule({'people':[{'id':'a','name':'A','days':[{'day_index':0,'status':'work','shifts':[shift]}]}]}, WEEK)

def test_work_without_hours_becomes_unknown():
    result=normalize_schedule({'people':[{'id':'a','name':'A','days':[{'day_index':0,'status':'work'}]}]},WEEK)
    assert result['people'][0]['days'][0]['status']=='unknown'

def test_non_image_and_malformed_base64_are_rejected():
    for encoded in ['!!!',base64.b64encode(b'<svg>no</svg>').decode()]:
        with pytest.raises(ValueError):
            validate_image(encoded)

def test_valid_png_mime_is_detected_not_trusted():
    import io
    from PIL import Image
    output=io.BytesIO(); Image.new('RGB',(5,5)).save(output,format='PNG')
    image=validate_image('data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode())
    assert image['mime_type']=='image/png'
    assert image['data']
