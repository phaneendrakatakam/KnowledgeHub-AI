import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import rag
from parsers.markdown_parser import (
    MarkdownParser
)


def test_markdown_parser_preserves_sections(
    tmp_path
):
    file_path = (
        tmp_path
        / "guide.md"
    )

    file_path.write_text(
        """
# Jenkins

General Jenkins information.

## Pipeline as Code

Pipeline as Code uses a Jenkinsfile.

### Declarative Pipeline

Declarative syntax is supported.

## Plugins

Jenkins has a plugin ecosystem.
        """.strip(),
        encoding="utf-8"
    )

    results = (
        MarkdownParser()
        .parse(
            str(file_path)
        )
    )

    sections = [
        item.section
        for item in results
    ]

    assert (
        "Jenkins"
        in sections
    )

    assert (
        "Jenkins > Pipeline as Code"
        in sections
    )

    assert (
        "Jenkins > Pipeline as Code "
        "> Declarative Pipeline"
        in sections
    )

    assert (
        "Jenkins > Plugins"
        in sections
    )


def test_markdown_heading_is_kept_in_content(
    tmp_path
):
    file_path = (
        tmp_path
        / "guide.md"
    )

    file_path.write_text(
        """
## Pipeline as Code

Pipeline as Code uses a Jenkinsfile.
        """.strip(),
        encoding="utf-8"
    )

    result = (
        MarkdownParser()
        .parse(
            str(file_path)
        )[0]
    )

    assert (
        "## Pipeline as Code"
        in result.content
    )

    assert (
        "Jenkinsfile"
        in result.content
    )


def test_markdown_without_heading_keeps_legacy_behavior(
    tmp_path
):
    file_path = (
        tmp_path
        / "notes.md"
    )

    file_path.write_text(
        "Plain Markdown content.",
        encoding="utf-8"
    )

    results = (
        MarkdownParser()
        .parse(
            str(file_path)
        )
    )

    assert len(results) == 1
    assert results[0].section is None
    assert (
        results[0].content
        == "Plain Markdown content."
    )


def test_unpack_search_result_supports_legacy_tuple():
    result = (
        1,
        10,
        "test.txt",
        2,
        "content",
        0.20
    )

    unpacked = (
        rag.unpack_search_result(
            result
        )
    )

    assert (
        unpacked["page_number"]
        is None
    )

    assert (
        unpacked["section"]
        is None
    )

    assert (
        unpacked["metadata"]
        == {}
    )


def test_unpack_search_result_preserves_v3_metadata():
    result = (
        1,
        10,
        "guide.pdf",
        2,
        "content",
        0.20,
        7,
        "Deployment",
        {
            "source_type":
                "pdf"
        }
    )

    unpacked = (
        rag.unpack_search_result(
            result
        )
    )

    assert (
        unpacked["page_number"]
        == 7
    )

    assert (
        unpacked["section"]
        == "Deployment"
    )

    assert (
        unpacked["metadata"]
        == {
            "source_type":
                "pdf"
        }
    )


def test_source_context_label_prefers_precise_location():
    label = (
        rag.build_source_context_label({
            "filename":
                "guide.pdf",
            "page_number":
                7,
            "section":
                "Deployment",
            "chunk_index":
                2
        })
    )

    assert (
        "Document: guide.pdf"
        in label
    )

    assert (
        "Page: 7"
        in label
    )

    assert (
        "Section: Deployment"
        in label
    )

    assert (
        "Chunk: 2"
        in label
    )