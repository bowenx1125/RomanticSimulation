import logging
import time
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.queue import SCENE_QUEUE_NAME, get_redis_client
from app.models import SimulationRun
from app.services.simulation.runtime import (
    apply_scene_runtime_result,
    execute_scene_runtime,
)
from app.services.simulation.service import (
    claim_scene_by_id,
    mark_scene_failed,
    mark_simulation_running,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_scene(scene_run_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        scene_run = claim_scene_by_id(db, scene_run_id, settings.claim_timeout_seconds)
        if scene_run is None:
            return

        simulation = db.get(SimulationRun, scene_run.simulation_run_id)
        if simulation is None:
            return

        mark_simulation_running(db, simulation)
        scene_run.status = "running"
        scene_run.started_at = scene_run.started_at or datetime.now(timezone.utc)
        db.add(scene_run)
        db.commit()

        try:
            execution = execute_scene_runtime(
                db,
                scene_run,
                simulation,
            )
            apply_scene_runtime_result(db, scene_run, simulation, execution)
            logger.info("Processed scene_run=%s simulation=%s", scene_run.id, simulation.id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scene execution failed: %s", scene_run.id)
            mark_scene_failed(db, scene_run, simulation, str(exc))


def main() -> None:
    settings = get_settings()
    redis_client = get_redis_client()
    logger.info("Worker started. queue=%s", SCENE_QUEUE_NAME)
    while True:
        item = redis_client.brpop(SCENE_QUEUE_NAME, timeout=settings.worker_poll_seconds)
        if item is None:
            time.sleep(0.2)
            continue
        _, scene_run_id = item
        process_scene(scene_run_id)


if __name__ == "__main__":
    main()
