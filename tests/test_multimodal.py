import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "backend"
    )
)

import pymupdf

import rag
import visual_analyzer
import parsers.pdf_parser as pdf_parser
import parsers.docx_parser as docx_parser


def test_format_visual_evidence():
    result = (
        visual_analyzer
        .format_visual_evidence({
            "visual_type":
                "architecture_diagram",
            "description":
                "Traffic flows through a load balancer.",
            "visible_text": [
                "Load Balancer",
                "API"
            ]
        })
    )

    assert (
        "architecture diagram"
        in result
    )

    assert (
        "Traffic flows through a load balancer."
        in result
    )

    assert (
        "Load Balancer"
        in result
    )


def test_pdf_image_only_page_can_create_visual_evidence(
    tmp_path,
    monkeypatch
):
    pdf_path = (
        tmp_path
        / "visual_only.pdf"
    )

    document = pymupdf.open()
    document.new_page()
    document.save(
        str(pdf_path)
    )
    document.close()

    def fake_analyze_visual(
        image_bytes,
        **kwargs
    ):
        assert image_bytes
        assert (
            kwargs["page_number"]
            == 1
        )

        return {
            "visual_type":
                "architecture_diagram",
            "evidence_text":
                (
                    "Visual type: architecture diagram\n\n"
                    "Description:\n"
                    "Client connects to API."
                )
        }

    monkeypatch.setattr(
        pdf_parser,
        "analyze_visual",
        fake_analyze_visual
    )

    results = (
        pdf_parser
        .PDFParser()
        .parse(
            str(pdf_path)
        )
    )

    assert len(results) == 1

    result = results[0]

    assert (
        result.page_number
        == 1
    )

    assert (
        result.metadata[
            "source_type"
        ]
        == "visual"
    )

    assert (
        result.metadata[
            "visual_type"
        ]
        == "architecture_diagram"
    )


def test_pdf_visual_failure_does_not_destroy_text(
    tmp_path,
    monkeypatch
):
    pdf_path = (
        tmp_path
        / "text.pdf"
    )

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "KnowledgeHub text evidence."
    )
    document.save(
        str(pdf_path)
    )
    document.close()

    monkeypatch.setattr(
        pdf_parser,
        "_page_has_useful_visual_candidate",
        lambda page, text:
            True
    )

    monkeypatch.setattr(
        pdf_parser,
        "analyze_visual",
        lambda *args, **kwargs:
            (_ for _ in ())
            .throw(
                RuntimeError(
                    "visual failure"
                )
            )
    )

    results = (
        pdf_parser
        .PDFParser()
        .parse(
            str(pdf_path)
        )
    )

    assert len(results) == 1

    assert (
        results[0].metadata[
            "source_type"
        ]
        == "pdf"
    )


def test_rag_visual_source_label():
    label = (
        rag.build_source_context_label({
            "filename":
                "architecture.pdf",
            "page_number":
                4,
            "section":
                None,
            "chunk_index":
                3,
            "metadata": {
                "source_type":
                    "visual",
                "visual_type":
                    "architecture_diagram"
            }
        })
    )

    assert (
        "Page: 4"
        in label
    )

    assert (
        "Visual: Architecture Diagram"
        in label
    )


def test_docx_tiny_image_filter_rejects_small_image():
    class FakeImage:
        px_width = 40
        px_height = 40

    class FakePart:
        blob = b"x" * 5000
        image = FakeImage()

    assert (
        docx_parser
        ._is_useful_docx_image(
            FakePart()
        )
        is False
    )


def test_docx_large_image_filter_accepts_large_image():
    class FakeImage:
        px_width = 800
        px_height = 500

    class FakePart:
        blob = b"x" * 5000
        image = FakeImage()

    assert (
        docx_parser
        ._is_useful_docx_image(
            FakePart()
        )
        is True
    )
