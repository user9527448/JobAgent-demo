"""Acceptance checks for attachment discovery, validation, and atomic storage."""

from __future__ import annotations

import asyncio
import io
import zipfile
from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from jobagent.core.exceptions import (
    ConfigurationError,
    PermanentJobAgentError,
    TransientJobAgentError,
)
from jobagent.crawlers import (
    AttachmentCandidate,
    AttachmentRecord,
    AttachmentStoragePolicy,
    AttachmentStorageService,
    AttachmentStoreStatus,
    HttpSourcePolicy,
    SourceHttpClient,
    discover_attachment_links,
)


class FakeAttachmentRepository:
    def __init__(self) -> None:
        self.record: AttachmentRecord | None = None
        self.failed_messages: list[str] = []

    async def get_or_create(
        self,
        document_id: int,
        candidate: AttachmentCandidate,
    ) -> AttachmentRecord:
        if self.record is None:
            self.record = AttachmentRecord(
                id=91,
                document_id=document_id,
                url=candidate.url,
                file_name=candidate.file_name,
                download_status="pending",
                mime_type=None,
                sha256=None,
                local_path=None,
                size_bytes=None,
                error_message=None,
            )
        return self.record

    async def mark_stored(
        self,
        attachment_id: int,
        *,
        mime_type: str,
        sha256: str,
        local_path: str,
        size_bytes: int,
    ) -> AttachmentRecord:
        assert self.record is not None
        assert attachment_id == self.record.id
        self.record = replace(
            self.record,
            download_status="stored",
            mime_type=mime_type,
            sha256=sha256,
            local_path=local_path,
            size_bytes=size_bytes,
            error_message=None,
        )
        return self.record

    async def mark_failed(self, attachment_id: int, *, error_message: str) -> None:
        assert self.record is not None
        assert attachment_id == self.record.id
        self.failed_messages.append(error_message)
        self.record = replace(
            self.record,
            download_status="failed",
            mime_type=None,
            sha256=None,
            local_path=None,
            size_bytes=None,
            error_message=error_message,
        )


class InterruptedStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"%PDF-1.7\npartial"
        raise httpx.ReadError("connection interrupted")


def _http_policy() -> HttpSourcePolicy:
    return HttpSourcePolicy(
        source_id=7,
        user_agent="JOBAGENT/0.1 (+https://example.invalid/contact)",
        min_interval_seconds=0,
        max_attempts=1,
    )


def _candidate(extension: str = ".pdf") -> AttachmentCandidate:
    return AttachmentCandidate(
        url=f"https://example.invalid/files/attachment{extension}",
        file_name=f"attachment{extension}",
        extension=extension,
    )


def _xlsx_bytes() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as workbook:
        workbook.writestr("[Content_Types].xml", "<Types />")
        workbook.writestr("xl/workbook.xml", "<workbook />")
    return output.getvalue()


def test_discovery_resolves_supported_links_deduplicates_and_sanitizes_names() -> None:
    candidates = discover_attachment_links(
        """
        <a href="../files/list.PDF?utm_source=page">岗位/名单.pdf</a>
        <a href="../files/list.PDF?utm_medium=duplicate">duplicate.pdf</a>
        <a href="/download?id=3">招聘岗位表.xlsx</a>
        <a href="files/legacy.xls"><strong>旧版表格</strong></a>
        <a href="javascript:void(0)">无效链接.pdf</a>
        <a href="files/readme.docx">unsupported</a>
        """,
        base_url="https://EXAMPLE.invalid/notices/1/index.html",
    )

    assert [(item.url, item.file_name, item.extension) for item in candidates] == [
        ("https://example.invalid/notices/files/list.PDF", "岗位_名单.pdf", ".pdf"),
        ("https://example.invalid/download?id=3", "招聘岗位表.xlsx", ".xlsx"),
        ("https://example.invalid/notices/1/files/legacy.xls", "legacy.xls", ".xls"),
    ]


def test_pdf_is_atomically_stored_and_repeated_discovery_reuses_it(tmp_path: Path) -> None:
    content = b"%PDF-1.7\nvalidated source bytes"
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"Content-Type": "application/pdf", "Content-Length": str(len(content))},
            content=content,
            request=request,
        )

    async def scenario() -> None:
        repository = FakeAttachmentRepository()
        service = AttachmentStorageService(AttachmentStoragePolicy(tmp_path), repository)
        async with SourceHttpClient(
            _http_policy(),
            transport=httpx.MockTransport(handler),
        ) as client:
            first = await service.store(11, _candidate(), client)
            second = await service.store(11, _candidate(), client)

        assert first.status is AttachmentStoreStatus.STORED
        assert second.status is AttachmentStoreStatus.REUSED
        assert first.attachment_id == second.attachment_id
        assert first.sha256 == second.sha256
        assert (tmp_path / first.local_path).read_bytes() == content
        assert list((tmp_path / ".tmp").iterdir()) == []

    asyncio.run(scenario())
    assert calls == 1


@pytest.mark.parametrize(
    ("headers", "content", "expected_code"),
    [
        (
            {"Content-Type": "text/html"},
            b"<html>upstream error</html>",
            "crawler.attachment_content_invalid",
        ),
        (
            {"Content-Type": "application/pdf", "Content-Length": "1000"},
            b"",
            "crawler.attachment_too_large",
        ),
        (
            {"Content-Type": "application/pdf"},
            b"%PDF-1.7\n" + b"x" * 100,
            "crawler.attachment_too_large",
        ),
    ],
)
def test_invalid_or_oversized_responses_are_recorded_without_final_files(
    tmp_path: Path,
    headers: dict[str, str],
    content: bytes,
    expected_code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers=headers, content=content, request=request)

    async def scenario() -> None:
        repository = FakeAttachmentRepository()
        service = AttachmentStorageService(
            AttachmentStoragePolicy(tmp_path, max_bytes=64),
            repository,
        )
        async with SourceHttpClient(
            _http_policy(),
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(PermanentJobAgentError) as captured_error:
                await service.store(11, _candidate(), client)

        assert captured_error.value.code == expected_code
        assert repository.record is not None
        assert repository.record.download_status == "failed"
        assert repository.failed_messages[0].startswith(expected_code)
        assert not (tmp_path / "objects").exists()
        temp_directory = tmp_path / ".tmp"
        assert not temp_directory.exists() or list(temp_directory.iterdir()) == []

    asyncio.run(scenario())


def test_interrupted_download_removes_partial_file_and_records_transient_failure(
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            stream=InterruptedStream(),
            request=request,
        )

    async def scenario() -> None:
        repository = FakeAttachmentRepository()
        service = AttachmentStorageService(AttachmentStoragePolicy(tmp_path), repository)
        async with SourceHttpClient(
            _http_policy(),
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(TransientJobAgentError) as captured_error:
                await service.store(11, _candidate(), client)

        assert captured_error.value.code == "crawler.attachment_download_interrupted"
        assert repository.record is not None
        assert repository.record.download_status == "failed"
        assert not (tmp_path / "objects").exists()
        assert list((tmp_path / ".tmp").iterdir()) == []

    asyncio.run(scenario())


def test_xlsx_signature_is_verified_even_with_generic_mime(tmp_path: Path) -> None:
    content = _xlsx_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/octet-stream"},
            content=content,
            request=request,
        )

    async def scenario() -> None:
        repository = FakeAttachmentRepository()
        service = AttachmentStorageService(AttachmentStoragePolicy(tmp_path), repository)
        async with SourceHttpClient(
            _http_policy(),
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await service.store(12, _candidate(".xlsx"), client)

        assert result.mime_type.endswith("spreadsheetml.sheet")
        assert (tmp_path / result.local_path).read_bytes() == content

    asyncio.run(scenario())


def test_invalid_storage_policy_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError) as captured_error:
        AttachmentStoragePolicy(tmp_path, max_bytes=0, chunk_bytes=0)

    assert captured_error.value.code == "crawler.attachment_policy_invalid"
