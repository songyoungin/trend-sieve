"""README 기반 저장소 정보 enrichment 모듈."""

import asyncio
import logging
from typing import TypedDict

import httpx

logger = logging.getLogger(__name__)


class MetadataResult(TypedDict):
    """메타데이터 결과 타입."""

    readme: str | None
    license: str | None
    is_open_source: bool


# 오픈소스 라이선스 목록
OPEN_SOURCE_LICENSES = {
    "mit",
    "apache-2.0",
    "gpl-2.0",
    "gpl-3.0",
    "lgpl-2.1",
    "lgpl-3.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "mpl-2.0",
    "unlicense",
    "isc",
    "agpl-3.0",
    "cc0-1.0",
    "wtfpl",
    "zlib",
}


class ReadmeEnricher:
    """README와 라이선스 정보를 가져온다."""

    def __init__(self, timeout: float = 10.0) -> None:
        """
        Args:
            timeout: HTTP 요청 타임아웃 (초)
        """
        self.timeout = timeout

    async def _fetch_readme(self, repo_name: str) -> str | None:
        """GitHub raw content에서 README를 가져온다."""
        readme_files = ["README.md", "readme.md", "Readme.md", "README.rst"]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for filename in readme_files:
                url = f"https://raw.githubusercontent.com/{repo_name}/HEAD/{filename}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        return str(response.text)
                except httpx.RequestError:
                    continue
        return None

    async def _fetch_license(self, repo_name: str) -> str | None:
        """GitHub API에서 라이선스 정보를 가져온다."""
        url = f"https://api.github.com/repos/{repo_name}/license"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    url,
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                if response.status_code == 200:
                    data: dict[str, dict[str, str]] = response.json()
                    license_info = data.get("license", {})
                    spdx_id = license_info.get("spdx_id", "")
                    return spdx_id.lower() if spdx_id else None
            except httpx.RequestError:
                pass
        return None

    def _is_open_source(self, license_id: str | None) -> bool:
        """라이선스가 오픈소스인지 확인한다."""
        if not license_id:
            return False
        return license_id.lower() in OPEN_SOURCE_LICENSES

    async def fetch_metadata(self, repo_name: str) -> MetadataResult:
        """저장소의 README와 라이선스 정보를 가져온다."""
        readme_task = self._fetch_readme(repo_name)
        license_task = self._fetch_license(repo_name)

        readme, license_id = await asyncio.gather(readme_task, license_task)

        return MetadataResult(
            readme=readme,
            license=license_id,
            is_open_source=self._is_open_source(license_id),
        )

    async def fetch_metadata_many(
        self,
        repo_names: list[str],
    ) -> dict[str, MetadataResult]:
        """여러 저장소의 메타데이터를 병렬로 가져온다."""
        tasks = [self.fetch_metadata(name) for name in repo_names]
        results = await asyncio.gather(*tasks)
        return dict(zip(repo_names, results, strict=True))
