import itertools
from typing import Any

from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.layout import Layout

from robusta_krr.core.abstract import formatters
from robusta_krr.core.models.allocations import RecommendationValue, format_recommendation_value, format_diff, NONE_LITERAL, NAN_LITERAL
from robusta_krr.core.models.result import ResourceScan, ResourceType, Result
from robusta_krr.core.models.config import settings
from robusta_krr.utils import resource_units


DEFAULT_INFO_COLOR = "grey27"
INFO_COLORS: dict[str, str] = {
    "OOMKill detected": "dark_red",
}


def _calculate_summary_stats(result: Result) -> dict[str, Any]:
    """Calculate summary statistics for the scan results."""
    stats = {
        "total_workloads": len(set((item.object.cluster, item.object.namespace, item.object.name) for item in result.scans)),
        "total_containers": len(result.scans),
        "by_severity": {"CRITICAL": 0, "WARNING": 0, "OK": 0, "GOOD": 0},
        "total_savings": {"cpu": 0, "memory": 0},
        "current_usage": {"cpu": 0, "memory": 0},
        "recommended_usage": {"cpu": 0, "memory": 0},
        "by_type": {}
    }
    
    for scan in result.scans:
        # Count by severity
        stats["by_severity"][scan.severity.name] += 1
        
        # Count by type
        if scan.object.kind not in stats["by_type"]:
            stats["by_type"][scan.object.kind] = 0
        stats["by_type"][scan.object.kind] += 1
        
        # Calculate resource savings
        for resource in ResourceType:
            current = scan.object.allocations.requests.get(resource)
            recommended = scan.recommended.requests.get(resource)
            
            if current is not None and recommended.value is not None:
                current_value = float(current) if current else 0
                recommended_value = float(recommended.value) if recommended.value else 0
                
                stats["current_usage"][resource.name.lower()] += current_value * scan.object.current_pods_count
                stats["recommended_usage"][resource.name.lower()] += recommended_value * scan.object.current_pods_count
                
                if current_value > recommended_value:
                    savings = (current_value - recommended_value) * scan.object.current_pods_count
                    stats["total_savings"][resource.name.lower()] += savings
    
    # Calculate percentages
    for resource in ["cpu", "memory"]:
        if stats["current_usage"][resource] > 0:
            stats[f"{resource}_reduction_percent"] = round(
                (stats["total_savings"][resource] / stats["current_usage"][resource]) * 100, 1
            )
        else:
            stats[f"{resource}_reduction_percent"] = 0
    
    return stats


def _format_summary_panel(stats: dict[str, Any]) -> Panel:
    """Create a summary panel with statistics."""
    summary_lines = [
        f"[bold]Scan Summary[/bold]",
        "",
        f"Total Workloads Scanned: [cyan]{stats['total_workloads']}[/cyan]",
        f"Total Containers: [cyan]{stats['total_containers']}[/cyan]",
        "",
        "[bold]Severity Breakdown:[/bold]",
        f"  Critical: [red]{stats['by_severity']['CRITICAL']}[/red]",
        f"  Warning: [yellow]{stats['by_severity']['WARNING']}[/yellow]",
        f"  OK: [green]{stats['by_severity']['OK']}[/green]",
        f"  Good: [bright_green]{stats['by_severity']['GOOD']}[/bright_green]",
        "",
        "[bold]Potential Savings:[/bold]",
        f"  CPU: [bright_green]{stats['total_savings']['cpu']:.0f}m[/bright_green] ([cyan]{stats['cpu_reduction_percent']}%[/cyan] reduction)",
        f"  Memory: [bright_green]{stats['total_savings']['memory']:.0f}Mi[/bright_green] ([cyan]{stats['memory_reduction_percent']}%[/cyan] reduction)",
        "",
        "[bold]Resource Totals:[/bold]",
        f"  Current CPU: {stats['current_usage']['cpu']:.0f}m → Recommended: {stats['recommended_usage']['cpu']:.0f}m",
        f"  Current Memory: {stats['current_usage']['memory']:.0f}Mi → Recommended: {stats['recommended_usage']['memory']:.0f}Mi",
    ]
    
    if stats["by_type"]:
        summary_lines.extend(["", "[bold]Workload Types:[/bold]"])
        for kind, count in stats["by_type"].items():
            summary_lines.append(f"  {kind}: {count}")
    
    return Panel("\n".join(summary_lines), title="Summary Statistics", border_style="blue")


def _format_request_str(item: ResourceScan, resource: ResourceType, selector: str) -> str:
    allocated = getattr(item.object.allocations, selector)[resource]
    info = item.recommended.info.get(resource)
    recommended = getattr(item.recommended, selector)[resource]
    severity = recommended.severity

    if allocated is None and recommended.value is None:
        return f"[{severity.color}]{NONE_LITERAL}[/{severity.color}]"

    diff = format_diff(allocated, recommended, selector, colored=True)
    if diff != "":
        diff = f"({diff}) "

    if info is None:
        info_formatted = ""
    else:
        color = INFO_COLORS.get(info, DEFAULT_INFO_COLOR)
        info_formatted = f"\n[{color}]({info})[/{color}]"

    return (
        diff
        + f"[{severity.color}]"
        + format_recommendation_value(allocated)
        + " -> "
        + format_recommendation_value(recommended.value)
        + f"[/{severity.color}]"
        + info_formatted
    )


def _format_total_diff(item: ResourceScan, resource: ResourceType, pods_current: int) -> str:
    selector = "requests"
    allocated = getattr(item.object.allocations, selector)[resource]
    recommended = getattr(item.recommended, selector)[resource]

    # if we have more than one pod, say so (this explains to the user why the total is different than the recommendation)
    if pods_current == 1:
        pods_info = ""
    else:
        pods_info = f"\n({pods_current} pods)"

    return f"{format_diff(allocated, recommended, selector, pods_current, colored=True)}{pods_info}"


@formatters.register(rich_console=True)
def table(result: Result) -> Table:
    """Format the result as text.

    :param result: The result to format.
    :type result: :class:`core.result.Result`
    :returns: The formatted results.
    :rtype: str
    """
    
    # Calculate and display summary statistics
    stats = _calculate_summary_stats(result)
    console = Console()
    console.print(_format_summary_panel(stats))
    console.print()

    table = Table(
        show_header=True,
        header_style="bold magenta",
        title=f"\n{result.description}\n" if result.description else None,
        title_justify="left",
        title_style="",
        caption=f"{result.score} points - {result.score_letter}",
    )

    cluster_count = len(set(item.object.cluster for item in result.scans))

    table.add_column("Number", justify="right", no_wrap=True)
    if cluster_count > 1 or settings.show_cluster_name:
        table.add_column("Cluster", style="cyan")
    table.add_column("Namespace", style="cyan")
    table.add_column("Name", style="cyan")
    table.add_column("Pods", style="cyan")
    table.add_column("Old Pods", style="cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Container", style="cyan")
    for resource in ResourceType:
        table.add_column(f"{resource.name} Diff")
        table.add_column(f"{resource.name} Requests")
        table.add_column(f"{resource.name} Limits")

    for _, group in itertools.groupby(
        enumerate(result.scans), key=lambda x: (x[1].object.cluster, x[1].object.namespace, x[1].object.name)
    ):
        group_items = list(group)

        for j, (i, item) in enumerate(group_items):
            last_row = j == len(group_items) - 1
            full_info_row = j == 0

            cells: list[Any] = [f"[{item.severity.color}]{i + 1}.[/{item.severity.color}]"]
            if cluster_count > 1 or settings.show_cluster_name:
                cells.append(item.object.cluster if full_info_row else "")
            cells += [
                item.object.namespace if full_info_row else "",
                item.object.name if full_info_row else "",
                f"{item.object.current_pods_count}" if full_info_row else "",
                f"{item.object.deleted_pods_count}" if full_info_row else "",
                item.object.kind if full_info_row else "",
                item.object.container,
            ]

            for resource in ResourceType:
                cells.append(_format_total_diff(item, resource, item.object.current_pods_count))
                cells += [_format_request_str(item, resource, selector) for selector in ["requests", "limits"]]

            table.add_row(*cells, end_section=last_row)

    return table
