from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from app.core.config import Settings
from app.core.database import async_session_factory
from app.ml.symbols import get_tracked_symbols
from app.ml.trainer import train_model_for_ticker
from app.ml.training_queue import get_training_queue, mark_training_symbol_complete

logger = logging.getLogger(__name__)


class MLPipelineScheduler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._task: asyncio.Task[None] | None = None
        self._queue_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if not self.settings.ml_scheduler_enabled:
            logger.info("ML scheduler disabled by configuration.")
            return

        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run_loop(), name="ml-pipeline-scheduler")

        if self._queue_task is None or self._queue_task.done():
            self._queue_task = asyncio.create_task(
                self._run_on_demand_queue(), name="ml-on-demand-training-queue"
            )

        logger.info("ML scheduler started.")

    async def stop(self) -> None:
        self._stop_event.set()
        for task in (self._task, self._queue_task):
            if task is None:
                continue

            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        logger.info("ML scheduler stopped.")

    async def _run_loop(self) -> None:
        initial_delay = max(0, self.settings.ml_scheduler_initial_delay_seconds)
        interval_seconds = max(1, self.settings.ml_retrain_interval_days) * 24 * 60 * 60

        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=initial_delay)
            return
        except TimeoutError:
            pass

        while not self._stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval_seconds)
            except TimeoutError:
                continue

    async def _run_on_demand_queue(self) -> None:
        queue = get_training_queue()
        while not self._stop_event.is_set():
            get_task = asyncio.create_task(queue.get())
            stop_task = asyncio.create_task(self._stop_event.wait())
            done, pending = await asyncio.wait(
                {get_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if stop_task in done:
                break

            symbol = get_task.result()
            try:
                await self._train_symbol(symbol)
            finally:
                mark_training_symbol_complete(symbol)
                queue.task_done()

    async def _train_symbol(self, symbol: str) -> None:
        async with async_session_factory() as session:
            try:
                training_run = await train_model_for_ticker(session, symbol, refresh_data=True)
                logger.info(
                    "ML training completed for %s with status=%s replaced=%s rows=%s",
                    symbol,
                    training_run.status,
                    training_run.replaced_production_model,
                    training_run.dataset_size,
                )
            except Exception:
                logger.exception("ML training failed unexpectedly for %s", symbol)

    async def run_once(self) -> None:
        logger.info("ML pipeline run started.")
        async with async_session_factory() as session:
            symbols = await get_tracked_symbols(session)

        for symbol in symbols:
            await self._train_symbol(symbol)

        logger.info("ML pipeline run finished for %s symbols.", len(symbols))
