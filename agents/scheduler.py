"""
Agent Scheduler / Worker Loop
Simple async worker that runs agent tasks periodically
(Replaces the "Ralph Loop" concept with a cleaner implementation)
"""

import asyncio
from typing import Callable, Optional, List, Any, Dict
from datetime import datetime
from loguru import logger
import json
from pathlib import Path


class ScheduledTask:
    """A scheduled task configuration"""
    
    def __init__(
        self,
        name: str,
        coro_func: Callable,
        interval: int,
        enabled: bool = True,
        max_retries: int = 3
    ):
        self.name = name
        self.coro_func = coro_func
        self.interval = interval  # seconds between runs
        self.enabled = enabled
        self.max_retries = max_retries
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0


class AgentScheduler:
    """
    Scheduler for running agent tasks periodically
    
    Features:
    - Multiple concurrent tasks
    - Configurable intervals
    - Error handling with retries
    - Start/stop control
    - Task statistics
    """

    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task_handles: Dict[str, asyncio.Task] = {}
        self._log_dir = Path("./logs/scheduler")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Agent Scheduler initialized")

    def add_task(
        self,
        name: str,
        coro_func: Callable,
        interval: int,
        enabled: bool = True,
        max_retries: int = 3
    ) -> ScheduledTask:
        """
        Add a scheduled task
        
        Args:
            name: Unique task name
            coro_func: Async function to call
            interval: Seconds between executions
            enabled: Whether task starts enabled
            max_retries: Max retries on error
            
        Returns:
            Created ScheduledTask
        """
        task = ScheduledTask(
            name=name,
            coro_func=coro_func,
            interval=interval,
            enabled=enabled,
            max_retries=max_retries
        )
        self.tasks[name] = task
        logger.info(f"Added scheduled task: {name} (interval: {interval}s)")
        return task

    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task"""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Removed task: {name}")
            return True
        return False

    def enable_task(self, name: str) -> bool:
        """Enable a task"""
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"Enabled task: {name}")
            return True
        return False

    def disable_task(self, name: str) -> bool:
        """Disable a task"""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Disabled task: {name}")
            return True
        return False

    async def _run_task(self, task: ScheduledTask) -> None:
        """Run a single task with error handling"""
        while self._running and task.enabled:
            try:
                task.next_run = datetime.now()
                
                # Execute the task
                logger.debug(f"Running task: {task.name}")
                await task.coro_func()
                
                # Update stats
                task.last_run = datetime.now()
                task.run_count += 1
                
                logger.debug(f"Task {task.name} completed successfully")
                
            except Exception as e:
                task.error_count += 1
                logger.error(f"Task {task.name} failed: {e}")
                
                # Log error to file
                self._log_task_error(task, e)
                
                # Retry logic
                retry_count = 0
                while retry_count < task.max_retries and self._running:
                    retry_count += 1
                    logger.warning(f"Retrying task {task.name} ({retry_count}/{task.max_retries})")
                    await asyncio.sleep(5)  # Wait before retry
                    
                    try:
                        await task.coro_func()
                        task.error_count -= 1  # Success, reduce error count
                        break
                    except Exception as retry_error:
                        logger.error(f"Retry {retry_count} failed for {task.name}: {retry_error}")
                
            # Wait for next interval
            if task.enabled:
                await asyncio.sleep(task.interval)

    def _log_task_error(self, task: ScheduledTask, error: Exception) -> None:
        """Log task error to file"""
        log_file = self._log_dir / f"{task.name}_errors.log"
        
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} | {type(error).__name__}: {error}\n")

    async def start(self) -> None:
        """Start all enabled tasks"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        logger.info("Starting scheduler...")
        
        # Start all enabled tasks
        for name, task in self.tasks.items():
            if task.enabled:
                handle = asyncio.create_task(self._run_task(task))
                self._task_handles[name] = handle
                logger.info(f"Started task: {name}")

    async def stop(self) -> None:
        """Stop all tasks"""
        if not self._running:
            return
        
        logger.info("Stopping scheduler...")
        self._running = False
        
        # Cancel all task handles
        for name, handle in self._task_handles.items():
            handle.cancel()
            try:
                await handle
            except asyncio.CancelledError:
                pass
        
        self._task_handles.clear()
        logger.info("Scheduler stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "running": self._running,
            "tasks": {
                name: {
                    "enabled": task.enabled,
                    "interval": task.interval,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "run_count": task.run_count,
                    "error_count": task.error_count
                }
                for name, task in self.tasks.items()
            }
        }

    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        if name not in self.tasks:
            return None
        
        task = self.tasks[name]
        return {
            "name": task.name,
            "enabled": task.enabled,
            "interval": task.interval,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "run_count": task.run_count,
            "error_count": task.error_count,
            "max_retries": task.max_retries
        }


# Example usage
async def example_task_1():
    """Example task that runs periodically"""
    logger.info(f"Task 1 running at {datetime.now()}")
    # Simulate work
    await asyncio.sleep(1)


async def example_task_2():
    """Another example task"""
    logger.info(f"Task 2 running at {datetime.now()}")
    # Could call AI agents, check markets, etc.


async def main():
    """Example scheduler usage"""
    scheduler = AgentScheduler()
    
    # Add tasks
    scheduler.add_task("task_1", example_task_1, interval=30)
    scheduler.add_task("task_2", example_task_2, interval=60)
    
    try:
        # Start scheduler
        await scheduler.start()
        
        # Run indefinitely (or until interrupted)
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted, stopping scheduler...")
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
