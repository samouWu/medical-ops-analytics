"""轻量日终调度器。生产环境可替换为Airflow/DolphinScheduler。"""
import time
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.database import db_session, init_db
from etl.jobs.pipeline import SOURCES, import_with_retry


def run_due_jobs(now=None):
    now = now or datetime.now()
    init_db()
    launched = []
    with db_session() as conn:
        jobs = [dict(row) for row in conn.execute("SELECT * FROM etl_job WHERE enabled=1")]
    for job in jobs:
        minute, hour, *_ = job["schedule"].split()
        if int(hour) == now.hour and int(minute) == now.minute and (not job["last_run"] or job["last_run"][:10] != now.date().isoformat()):
            source = job["source_table"]
            result = import_with_retry(source, DATA_DIR / SOURCES[source]["path"], rebuild=False, incremental=True, retry_limit=job["retry_limit"])
            launched.append(result)
    if launched:
        from etl.jobs.pipeline import rebuild_warehouse
        rebuild_warehouse()
    return launched


def main():
    while True:
        run_due_jobs()
        time.sleep(30)


if __name__ == "__main__":
    main()
