import pytest
from fastapi import HTTPException
from services.usage_limits import reserve_job, release_job

def test_two_jobs_allowed_third_rejected_and_release_recovers(tmp_path):
    path=str(tmp_path/'jobs.db')
    a=reserve_job(path,'alice');b=reserve_job(path,'alice')
    with pytest.raises(HTTPException) as exc: reserve_job(path,'alice')
    assert exc.value.status_code==429
    c=reserve_job(path,'bob')
    release_job(path,a)
    assert reserve_job(path,'alice')
    release_job(path,b);release_job(path,c)
