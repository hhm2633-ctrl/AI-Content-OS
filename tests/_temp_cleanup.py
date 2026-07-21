import logging
import shutil
import time
from pathlib import Path


LOGGER = logging.getLogger(__name__)


def remove_temp_tree_with_retry(path, *, attempts=3, initial_delay_seconds=0.05):
    """Remove a test temp tree without hiding persistent Windows failures."""
    target = Path(path)
    for attempt in range(1, attempts + 1):
        try:
            shutil.rmtree(target)
            return
        except FileNotFoundError:
            return
        except OSError:
            if attempt == attempts:
                LOGGER.error(
                    "temporary_directory_cleanup_failed path=%s attempt=%d/%d",
                    target,
                    attempt,
                    attempts,
                    exc_info=True,
                )
                raise

            delay_seconds = initial_delay_seconds * (2 ** (attempt - 1))
            LOGGER.warning(
                "temporary_directory_cleanup_retry path=%s attempt=%d/%d delay_seconds=%.2f",
                target,
                attempt,
                attempts,
                delay_seconds,
                exc_info=True,
            )
            time.sleep(delay_seconds)
