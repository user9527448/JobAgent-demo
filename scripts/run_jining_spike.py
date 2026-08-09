"""Run the one-off JAI-005 live source validation sequentially and politely."""

from __future__ import annotations

import json
import time

import httpx

from jobagent.spikes.jining import (
    LIST_URL,
    TARGET_DETAIL_PATH,
    extract_pdf_pages,
    parse_detail,
    parse_list,
)

USER_AGENT = "JOBAGENT/0.1 (+personal recruitment intelligence research; low-frequency)"
REQUEST_INTERVAL_SECONDS = 1.0


def main() -> int:
    """Fetch exactly one list, detail, and PDF and print a validation summary."""
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        list_response = _get(client, LIST_URL, expected_type="text/html")
        discovered = parse_list(list_response.content)
        selected = next(
            (item for item in discovered if item.url.endswith(TARGET_DETAIL_PATH)),
            None,
        )
        if selected is None:
            raise RuntimeError(
                "The verified target announcement is no longer present on the list page."
            )

        time.sleep(REQUEST_INTERVAL_SECONDS)
        detail_response = _get(client, selected.url, expected_type="text/html")
        detail = parse_detail(detail_response.content, detail_url=selected.url)

        time.sleep(REQUEST_INTERVAL_SECONDS)
        attachment_response = _get(
            client,
            detail.attachments[0].url,
            expected_type="application/pdf",
        )
        pages = extract_pdf_pages(attachment_response.content)

    print(
        json.dumps(
            {
                "discovered_count": len(discovered),
                "title": detail.title,
                "published_at": detail.published_at.isoformat(),
                "body_characters": len(detail.body_text),
                "attachment_count": len(detail.attachments),
                "pdf_pages": len(pages),
                "first_page_preview": pages[0].text[:120],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _get(client: httpx.Client, url: str, *, expected_type: str) -> httpx.Response:
    response = client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if expected_type not in content_type:
        raise RuntimeError(f"Unexpected content type for {url}: {content_type!r}.")
    return response


if __name__ == "__main__":
    raise SystemExit(main())
