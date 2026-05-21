"""
Orchestrator — dispatches Celery scan tasks based on scan scope.

Called by POST /scans after the scan record is created.
Future sprints add network_worker and web_worker here.
"""
import logging
import uuid

from backend.models.scan import ScanScope

logger = logging.getLogger(__name__)


def dispatch_scan(scan_id: uuid.UUID, scope: ScanScope) -> None:
    """
    Dispatch the appropriate Celery tasks for the given scope.
    Tasks are imported inline to avoid circular imports at module load time.
    """
    from backend.workers.recon_worker import run_recon

    sid = str(scan_id)
    logger.info("Dispatching scan %s (scope=%s)", sid[:8], scope.value)

    if scope in (ScanScope.recon, ScanScope.full):
        run_recon.delay(sid)

    # Sprint 4: network_worker dispatched here
    # Sprint 5: web_worker dispatched here
