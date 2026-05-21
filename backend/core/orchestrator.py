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
    from backend.workers.network_worker import run_network_scan
    from backend.workers.web_worker import run_web_scan

    sid = str(scan_id)
    logger.info("Dispatching scan %s (scope=%s)", sid[:8], scope.value)

    if scope in (ScanScope.recon, ScanScope.full):
        run_recon.delay(sid)

    if scope in (ScanScope.network, ScanScope.full):
        run_network_scan.delay(sid)

    if scope in (ScanScope.web, ScanScope.full):
        run_web_scan.delay(sid)
