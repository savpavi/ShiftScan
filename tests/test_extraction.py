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


def test_headerless_row_of_seven_cells_is_mapped_in_visual_order_for_review():
    cells = [{'status': 'work', 'shifts': [{'start': '09:00', 'end': '18:00'}], 'source_text': '09-18'}] * 4
    cells += [{'status': 'off', 'source_text': 'OFF'}, {'status': 'unknown'}, {'status': 'off', 'source_text': 'OFF'}]
    result = normalize_schedule({'people': [{'id': 'a', 'name': 'A', 'days': cells}]}, WEEK)
    days = result['people'][0]['days']
    assert [d['status'] for d in days] == ['work'] * 4 + ['off', 'unknown', 'off']
    assert days[0]['shifts'] == [{'start': '09:00', 'end': '18:00'}]
    assert all('sırayla' in d['issue'] for d in days)  # her gün kontrol istenir
    assert not any('aktarılmadı' in w for w in result['warnings'])
    assert any('başlığı yok' in w for w in result['warnings'])


def test_headerless_cells_use_column_when_given():
    cells = [{'column': 6 - i, 'status': 'off' if i else 'work',
              'shifts': [] if i else [{'start': '10:00', 'end': '19:00'}]} for i in range(7)]
    days = normalize_schedule({'people': [{'id': 'a', 'name': 'A', 'days': cells}]}, WEEK)['people'][0]['days']
    assert days[6]['status'] == 'work' and days[0]['status'] == 'off'


def test_headerless_cells_not_mapped_when_count_is_not_seven():
    cells = [{'status': 'work', 'shifts': [{'start': '09:00', 'end': '18:00'}]}] * 5
    result = normalize_schedule({'people': [{'id': 'a', 'name': 'A', 'days': cells}]}, WEEK)
    assert all(d['status'] == 'unknown' for d in result['people'][0]['days'])
    assert any('aktarılmadı' in w for w in result['warnings'])



def _week_people():
    off = [{'day_index': i, 'status': 'off'} for i in range(7)]
    return [{'id': 'e', 'name': 'Ege Bostancı', 'days': off}, {'id': 'h', 'name': 'HÜLYA K.', 'days': off}]


def test_duty_row_is_attached_to_matching_people_by_first_name():
    raw = {'people': _week_people(), 'duties': [{'name': 'DİJİTAL ACENTELİK', 'days': [
        {'day_index': 0, 'people': ['EGE']}, {'day_index': 1, 'people': ['Hulya', 'Anıl']},
        {'day_index': 3, 'people': ['Yağmur / Ege']}]}]}
    result = normalize_schedule(raw, WEEK)
    ege, hulya = result['people']
    assert [i for i, d in enumerate(ege['days']) if d.get('duties')] == [0, 3]
    assert ege['days'][0]['duties'] == ['DİJİTAL ACENTELİK']
    assert [i for i, d in enumerate(hulya['days']) if d.get('duties')] == [1]
    assert result['duties'] == ['DİJİTAL ACENTELİK']


def test_duty_row_without_days_is_reported_not_guessed():
    raw = {'people': _week_people(), 'duties': [{'name': 'Nöbet', 'days': [{'people': ['Ege']}]}]}
    result = normalize_schedule(raw, WEEK)
    assert not any(d.get('duties') for p in result['people'] for d in p['days'])
    assert any('Nöbet' in w for w in result['warnings'])


def test_week_hint_suggests_the_printed_monday():
    from datetime import date
    requested = date(2026, 10, 26)
    result = normalize_schedule({'people': _week_people(), 'week_hint': '02.11'}, requested)
    assert result['suggested_week_start'] == '2026-11-02'
    assert result['week_start'] == '2026-10-26'  # kullanıcı onaylamadan değişmez


def test_week_hint_ignored_when_not_monday_or_same_week():
    from datetime import date
    requested = date(2026, 10, 26)
    assert 'suggested_week_start' not in normalize_schedule({'people': _week_people(), 'week_hint': '03.11'}, requested)
    assert 'suggested_week_start' not in normalize_schedule({'people': _week_people(), 'week_hint': '26.10'}, requested)
    assert 'suggested_week_start' not in normalize_schedule({'people': _week_people(), 'week_hint': '31.02'}, requested)
