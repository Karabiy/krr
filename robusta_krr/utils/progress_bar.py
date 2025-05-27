from alive_progress import alive_bar
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from typing import Optional
import logging

from robusta_krr.core.models.config import settings

logger = logging.getLogger("krr")


class ProgressBar:
    """
    Progress bar for displaying progress of gathering recommendations.

    Use `ProgressBar` as a context manager to automatically handle the progress bar.
    Use `progress` method to step the progress bar.
    """

    def __init__(self, total: Optional[int] = None, title: str = "Processing", use_rich: bool = True, **kwargs) -> None:
        self.show_bar = not settings.quiet and not settings.log_to_stderr
        self.use_rich = use_rich and self.show_bar
        self.total = total
        self.title = title
        self.current = 0
        
        if self.use_rich:
            # Use Rich progress bar for better integration with console output
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=settings.logging_console,
                transient=True,  # Remove progress bar after completion
            )
        elif self.show_bar:
            # Fallback to alive_progress if rich is not suitable
            self.alive_bar = alive_bar(total=total, title=title, **kwargs, enrich_print=False)
        
        self.task_id = None

    def __enter__(self):
        if self.use_rich:
            self.progress.__enter__()
            self.task_id = self.progress.add_task(self.title, total=self.total)
        elif self.show_bar:
            self.bar = self.alive_bar.__enter__()
        return self

    def progress(self, advance: int = 1, description: Optional[str] = None):
        """Update progress bar"""
        self.current += advance
        
        if self.use_rich and self.task_id is not None:
            if description:
                self.progress.update(self.task_id, description=f"{self.title}: {description}")
            self.progress.update(self.task_id, advance=advance)
        elif self.show_bar:
            self.bar()

    def update_total(self, total: int):
        """Update the total count for the progress bar"""
        self.total = total
        if self.use_rich and self.task_id is not None:
            self.progress.update(self.task_id, total=total)

    def __exit__(self, *args):
        if self.use_rich:
            self.progress.__exit__(*args)
        elif self.show_bar:
            self.alive_bar.__exit__(*args)
