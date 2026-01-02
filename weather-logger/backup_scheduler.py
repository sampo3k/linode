#!/usr/bin/env python3
"""
Weather Logger - Backup Scheduler

Runs database backups on a schedule (cron-like).
"""
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from weather_logger import Config, ConfigError
from weather_logger.utils import setup_logging
from backup import BackupManager


logger = logging.getLogger(__name__)


class BackupScheduler:
    """
    Schedules and executes database backups.
    """

    def __init__(self, config: Config):
        """
        Initialize backup scheduler.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.running = False
        self.backup_manager = BackupManager(config)

        # Get backup schedule (cron format)
        backup_config = config.get("backup", {})
        self.schedule = backup_config.get("schedule", "0 2 * * *")  # Daily at 2am

        # Parse cron schedule to get hour and minute
        self.backup_hour, self.backup_minute = self._parse_schedule(self.schedule)

        logger.info(f"Backup scheduler initialized")
        logger.info(f"Backup schedule: Daily at {self.backup_hour:02d}:{self.backup_minute:02d}")

    def _parse_schedule(self, cron_string: str) -> tuple:
        """
        Parse simple cron schedule string.

        Supports format: "minute hour * * *"
        Example: "0 2 * * *" = 2:00 AM daily

        Args:
            cron_string: Cron schedule string

        Returns:
            Tuple of (hour, minute)
        """
        parts = cron_string.split()
        if len(parts) < 2:
            logger.warning(f"Invalid cron schedule: {cron_string}, using default 2:00 AM")
            return (2, 0)

        try:
            minute = int(parts[0])
            hour = int(parts[1])
            return (hour, minute)
        except ValueError:
            logger.warning(f"Invalid cron schedule: {cron_string}, using default 2:00 AM")
            return (2, 0)

    def _time_until_next_backup(self) -> float:
        """
        Calculate seconds until next scheduled backup.

        Returns:
            Seconds until next backup
        """
        now = datetime.now()
        target = now.replace(hour=self.backup_hour, minute=self.backup_minute, second=0, microsecond=0)

        # If target time has passed today, schedule for tomorrow
        if target <= now:
            target = target.replace(day=target.day + 1)

        time_until = (target - now).total_seconds()
        return time_until

    def run(self):
        """
        Run the backup scheduler.

        Waits for scheduled time and executes backups.
        """
        if not self.backup_manager.enabled:
            logger.info("Backups are disabled in configuration")
            print("Backups are disabled in configuration")
            print("Set backup.enabled=true in config.yaml to enable")
            return

        self.running = True
        logger.info("Backup scheduler started")
        print(f"Backup scheduler running - backups at {self.backup_hour:02d}:{self.backup_minute:02d} daily")

        # Run initial backup if user wants
        # (commented out by default - uncomment to backup on startup)
        # logger.info("Running initial backup...")
        # self.backup_manager.create_backup()

        while self.running:
            try:
                # Calculate time until next backup
                seconds_until = self._time_until_next_backup()
                next_backup_time = datetime.now().timestamp() + seconds_until

                logger.info(f"Next backup in {seconds_until / 3600:.1f} hours "
                           f"at {datetime.fromtimestamp(next_backup_time)}")

                # Sleep in 1-minute intervals to allow graceful shutdown
                while self.running and seconds_until > 0:
                    sleep_time = min(60, seconds_until)  # Sleep max 1 minute at a time
                    time.sleep(sleep_time)
                    seconds_until -= sleep_time

                if not self.running:
                    break

                # Time for backup!
                logger.info("Executing scheduled backup...")
                print(f"\n[{datetime.now()}] Running scheduled backup...")

                success = self.backup_manager.create_backup()

                if success:
                    logger.info("Scheduled backup completed successfully")
                    print("✓ Backup completed successfully")
                else:
                    logger.error("Scheduled backup failed")
                    print("✗ Backup failed - check logs")

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.exception(f"Unexpected error in scheduler loop: {e}")
                time.sleep(60)  # Wait before retrying

        self.stop()

    def stop(self):
        """Stop the scheduler gracefully."""
        self.running = False
        logger.info("Backup scheduler stopped")


def setup_signal_handlers(scheduler: BackupScheduler):
    """
    Setup signal handlers for graceful shutdown.

    Args:
        scheduler: BackupScheduler instance
    """
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal")
        scheduler.stop()
        sys.exit(0)

    # Handle SIGINT (Ctrl+C) and SIGTERM (Docker stop)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point for backup scheduler."""
    print("Weather Logger - Backup Scheduler")
    print("=" * 60)

    # Load configuration
    try:
        config = Config.load_from_file("config.yaml")
    except ConfigError as e:
        print(f"Configuration error: {e}")
        return 1

    # Setup logging
    log_config = config.get_logging_config()
    setup_logging(
        log_file=log_config["file"],
        log_level=log_config.get("level", "INFO"),
        log_format=log_config["format"],
    )

    logger.info("=" * 60)
    logger.info("Weather Logger - Backup Scheduler")
    logger.info("=" * 60)

    # Create scheduler
    try:
        scheduler = BackupScheduler(config)
    except Exception as e:
        logger.exception(f"Failed to initialize scheduler: {e}")
        return 1

    # Setup signal handlers
    setup_signal_handlers(scheduler)

    # Run scheduler
    try:
        scheduler.run()
        return 0
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
