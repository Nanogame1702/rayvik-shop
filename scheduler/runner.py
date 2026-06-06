import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot
from services import scheduled_repo
from utils.broadcast_sender import send_broadcast

log = logging.getLogger(__name__)

class SchedulerRunner:
    def __init__(self, bot: Bot, admin_chat_id: Optional[int] = None):
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self._task = None
        self._stop = asyncio.Event()

    async def start(self):
        await scheduled_repo.ensure_schema()
        
        # Синхронизация recurring broadcasts при старте
        try:
            from services.recurring_service import RecurringBroadcastService
            await RecurringBroadcastService.sync_recurring_schedules(self.bot)
            log.info("Recurring broadcasts synchronized")
        except Exception as e:
            log.exception("Error syncing recurring broadcasts: %s", e)
        
        self._task = asyncio.create_task(self._run_loop(), name="broadcast_scheduler_runner")

    async def stop(self):
        if self._task:
            self._stop.set()
            await self._task

    async def _run_loop(self):
        while not self._stop.is_set():
            try:
                now = datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat()
                due = await scheduled_repo.get_due(now_utc_iso=now, limit=3)
                for job in due:
                    await scheduled_repo.mark_status(job["id"], "sending")
                    success = False
                    error_msg = None
                    recipients_count = 0
                    
                    try:
                        parsed = None
                        if job.get("keyboard_json"):
                            try:
                                parsed = json.loads(job["keyboard_json"])
                            except Exception:
                                parsed = None
                        payload = parsed if parsed is not None else None
                        async def progress(sent, total, ok, failed):
                            return
                        total, ok, failed = await send_broadcast(
                            self.bot,
                            audience=job["audience"],
                            text=job["text"],
                            parse_mode=job.get("parse_mode") or "HTML",
                            keyboard_layout_or_payload=payload,
                            progress_cb=progress,
                        )
                        await scheduled_repo.update_stats(job["id"], total, ok, failed)
                        await scheduled_repo.mark_status(job["id"], "done")
                        success = True
                        recipients_count = ok
                    except Exception as e:
                        log.exception("Scheduled job %s failed: %s", job["id"], e)
                        error_msg = str(e)[:300]
                        await scheduled_repo.mark_status(job["id"], "failed", last_error=error_msg)
                    
                    # Обработка recurring broadcast после отправки
                    try:
                        from services.recurring_service import RecurringBroadcastService
                        await RecurringBroadcastService.process_completed_broadcast(
                            scheduled_task=job,
                            success=success,
                            error=error_msg,
                            recipients_count=recipients_count
                        )
                    except Exception as e:
                        log.exception("Error processing recurring broadcast: %s", e)
            except Exception as e:
                log.exception("Scheduler loop error: %s", e)
            await asyncio.sleep(30)

_runner: Optional[SchedulerRunner] = None

async def start_runner(bot: Bot, admin_chat_id: Optional[int] = None):
    global _runner
    if _runner is None:
        _runner = SchedulerRunner(bot, admin_chat_id)
        await _runner.start()
    return _runner

async def stop_runner():
    global _runner
    if _runner is not None:
        await _runner.stop()
        _runner = None
