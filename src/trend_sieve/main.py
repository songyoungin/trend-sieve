"""CLI 엔트리포인트."""

import asyncio
from enum import Enum
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from trend_sieve.filters import GeminiFilter
from trend_sieve.models import FilteredRepository
from trend_sieve.sources import GitHubTrendingSource

console = Console()


class Since(str, Enum):
    """기간 필터 옵션."""

    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


app = typer.Typer(
    name="trend-sieve",
    help="GitHub Trending에서 AI/LLM 관련 저장소를 필터링합니다.",
    no_args_is_help=False,
)


def _render_results(filtered: list[FilteredRepository]) -> None:
    """필터링 결과를 Rich로 렌더링한다."""
    if not filtered:
        console.print("\n[yellow]관심 키워드와 관련된 저장소가 없습니다.[/yellow]")
        return

    # 헤더
    console.print()
    console.rule("[bold blue]🔥 오늘의 AI/LLM 트렌드 저장소[/bold blue]")
    console.print()

    # 요약 테이블
    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("저장소", style="bold")
    table.add_column("언어", width=12)
    table.add_column("⭐ Stars", justify="right", width=15)
    table.add_column("관련성", justify="center", width=8)

    for i, item in enumerate(filtered, 1):
        repo = item.repository
        stars_text = f"{repo.stars:,} [green](+{repo.stars_today:,})[/green]"
        relevance_text = f"[{'green' if item.relevance_score >= 8 else 'yellow'}]{item.relevance_score}/10[/]"
        table.add_row(
            str(i),
            f"[link={repo.url}]{repo.name}[/link]",
            repo.language or "-",
            stars_text,
            relevance_text,
        )

    console.print(table)
    console.print()

    # 상세 정보
    for i, item in enumerate(filtered, 1):
        repo = item.repository
        keywords = ", ".join(item.matched_interests)

        header = f"[bold]{i}. {repo.name}[/bold]  [dim]|[/dim]  🏷️ {keywords}"
        content = f"{item.summary}\n\n[dim]🔗 {repo.url}[/dim]"

        console.print(Panel(Markdown(content), title=header, border_style="blue"))
        console.print()


async def _run(language: str | None, since: str) -> None:
    """메인 파이프라인을 실행한다."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        # 1. GitHub Trending에서 저장소 수집
        task = progress.add_task("GitHub Trending 데이터 수집 중...", total=None)
        source = GitHubTrendingSource(since=since, language=language)
        repositories = await source.fetch()
        progress.update(
            task,
            description=f"[green]✓[/green] 수집 완료: {len(repositories)}개 저장소",
        )
        progress.remove_task(task)

        if not repositories:
            console.print("[yellow]수집된 저장소가 없습니다.[/yellow]")
            return

        # 2. Gemini로 필터링 및 요약
        task = progress.add_task("AI 필터링 및 요약 중...", total=None)
        gemini_filter = GeminiFilter()
        filtered = await gemini_filter.filter(repositories)
        progress.update(
            task,
            description=f"[green]✓[/green] 필터링 완료: {len(filtered)}개 관련 저장소",
        )
        progress.remove_task(task)

    # 3. 결과 출력
    _render_results(filtered)


@app.command()
def main(
    language: Annotated[
        str | None,
        typer.Option(
            "--lang",
            "-l",
            help="프로그래밍 언어 필터 (예: python, rust, go)",
        ),
    ] = None,
    since: Annotated[
        Since,
        typer.Option(
            "--since",
            "-s",
            help="기간 필터",
        ),
    ] = Since.daily,
) -> None:
    """GitHub Trending에서 AI/LLM 관련 저장소를 필터링합니다."""
    try:
        asyncio.run(_run(language, since.value))
    except KeyboardInterrupt:
        console.print("\n[dim]중단됨[/dim]")
        raise typer.Exit(0) from None
    except Exception as e:
        console.print(f"[red]오류 발생: {e}[/red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
