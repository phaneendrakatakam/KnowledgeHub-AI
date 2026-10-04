from pathlib import Path

import pymupdf

from .base import (
    BaseParser,
    NormalizedContent
)
from visual_analyzer import (
    analyze_visual
)


PDF_RENDER_SCALE = 1.6
MIN_IMAGE_WIDTH = 250
MIN_IMAGE_HEIGHT = 140
MIN_IMAGE_PAGE_RATIO = 0.10
MIN_VECTOR_DRAWINGS = 8


def _page_has_useful_visual_candidate(
    page,
    extracted_text: str
) -> bool:
    """
    Lightweight filtering before invoking Gemini.

    A page is considered a visual candidate when:
    - it has no extractable text (scanned/image-only page), or
    - it contains a sufficiently large embedded image, or
    - it contains enough vector drawing objects to plausibly
      represent a diagram/chart/flowchart.
    """

    if not extracted_text.strip():
        return True

    page_area = max(
        float(
            page.rect.width
            * page.rect.height
        ),
        1.0
    )

    try:
        image_info = (
            page.get_image_info(
                xrefs=True
            )
        )
    except Exception:
        image_info = []

    for info in image_info:
        width = int(
            info.get(
                "width",
                0
            )
            or 0
        )

        height = int(
            info.get(
                "height",
                0
            )
            or 0
        )

        bbox = info.get(
            "bbox"
        )

        bbox_ratio = 0.0

        if bbox:
            try:
                rect = pymupdf.Rect(
                    bbox
                )

                bbox_ratio = (
                    float(
                        rect.width
                        * rect.height
                    )
                    / page_area
                )
            except Exception:
                bbox_ratio = 0.0

        if (
            (
                width
                >= MIN_IMAGE_WIDTH
                and height
                >= MIN_IMAGE_HEIGHT
            )
            or bbox_ratio
            >= MIN_IMAGE_PAGE_RATIO
        ):
            return True

    try:
        drawings = (
            page.get_drawings()
        )
    except Exception:
        drawings = []

    return (
        len(drawings)
        >= MIN_VECTOR_DRAWINGS
    )


def _render_page_png(
    page
) -> bytes:
    matrix = pymupdf.Matrix(
        PDF_RENDER_SCALE,
        PDF_RENDER_SCALE
    )

    pixmap = page.get_pixmap(
        matrix=matrix,
        alpha=False
    )

    return pixmap.tobytes(
        "png"
    )


class PDFParser(BaseParser):

    supported_extensions = (
        ".pdf",
    )


    def parse(
        self,
        file_path: str
    ) -> list[NormalizedContent]:

        path = Path(
            file_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: "
                f"{file_path}"
            )

        try:
            document = pymupdf.open(
                str(path)
            )
        except Exception as error:
            raise ValueError(
                "The PDF file could not be opened "
                "or is malformed."
            ) from error

        results = []

        try:
            for page_index, page in enumerate(
                document
            ):
                page_number = (
                    page_index + 1
                )

                text = (
                    page
                    .get_text()
                    .strip()
                )

                if text:
                    results.append(
                        NormalizedContent(
                            content=
                                text,
                            filename=
                                path.name,
                            file_type=
                                "pdf",
                            page_number=
                                page_number,
                            metadata={
                                "source_type":
                                    "pdf"
                            }
                        )
                    )

                if not _page_has_useful_visual_candidate(
                    page,
                    text
                ):
                    continue

                try:
                    analysis = (
                        analyze_visual(
                            _render_page_png(
                                page
                            ),
                            mime_type=
                                "image/png",
                            filename=
                                path.name,
                            page_number=
                                page_number
                        )
                    )
                except Exception as error:
                    print(
                        "Visual analysis skipped "
                        f"for {path.name} "
                        f"page {page_number}: "
                        f"{error}"
                    )

                    analysis = None

                if not analysis:
                    continue

                results.append(
                    NormalizedContent(
                        content=
                            analysis[
                                "evidence_text"
                            ],
                        filename=
                            path.name,
                        file_type=
                            "pdf",
                        page_number=
                            page_number,
                        metadata={
                            "source_type":
                                "visual",
                            "visual_type":
                                analysis[
                                    "visual_type"
                                ],
                            "analysis_method":
                                "gemini_multimodal"
                        }
                    )
                )

        finally:
            document.close()

        if not results:
            raise ValueError(
                "The PDF does not contain "
                "any usable text or visual evidence."
            )

        return results