from hashlib import sha256
from pathlib import Path
from typing import Iterator, Union

from docx import Document
from docx.document import (
    Document as DocumentObject
)
from docx.table import Table
from docx.text.paragraph import Paragraph

from .base import (
    BaseParser,
    NormalizedContent
)
from visual_analyzer import (
    analyze_visual
)


MIN_DOCX_IMAGE_WIDTH = 180
MIN_DOCX_IMAGE_HEIGHT = 120
MIN_DOCX_IMAGE_BYTES = 2500


def iter_block_items(
    document: DocumentObject
) -> Iterator[
    Union[
        Paragraph,
        Table
    ]
]:
    """
    Yield paragraphs and tables in their original
    document order.
    """

    for child in (
        document
        .element
        .body
        .iterchildren()
    ):
        if child.tag.endswith(
            "}p"
        ):
            yield Paragraph(
                child,
                document
            )

        elif child.tag.endswith(
            "}tbl"
        ):
            yield Table(
                child,
                document
            )


def _paragraph_image_relationship_ids(
    paragraph: Paragraph
) -> list[str]:
    try:
        return list(
            paragraph
            ._p
            .xpath(
                ".//a:blip/@r:embed"
            )
        )
    except Exception:
        return []


def _image_dimensions(
    image_part
):
    try:
        image = (
            image_part.image
        )

        return (
            int(
                image.px_width
            ),
            int(
                image.px_height
            )
        )
    except Exception:
        return (
            None,
            None
        )


def _is_useful_docx_image(
    image_part
) -> bool:
    blob = getattr(
        image_part,
        "blob",
        b""
    )

    if not blob:
        return False

    width, height = (
        _image_dimensions(
            image_part
        )
    )

    if (
        width is not None
        and height is not None
    ):
        return (
            width
            >= MIN_DOCX_IMAGE_WIDTH
            and height
            >= MIN_DOCX_IMAGE_HEIGHT
        )

    return (
        len(blob)
        >= MIN_DOCX_IMAGE_BYTES
    )


def _image_mime_type(
    image_part
) -> str:
    content_type = getattr(
        image_part,
        "content_type",
        ""
    )

    if content_type:
        return content_type

    return "image/png"


class DOCXParser(BaseParser):

    supported_extensions = (
        ".docx",
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
            document = Document(
                str(path)
            )
        except Exception as error:
            raise ValueError(
                "The DOCX file could not be "
                "opened or is malformed."
            ) from error

        results: list[
            NormalizedContent
        ] = []

        current_section: (
            str | None
        ) = None

        current_parts: list[
            str
        ] = []

        seen_images = set()

        def flush_section():
            nonlocal current_parts

            content = "\n".join(
                part.strip()
                for part
                in current_parts
                if (
                    part
                    and part.strip()
                )
            ).strip()

            if content:
                results.append(
                    NormalizedContent(
                        content=
                            content,
                        filename=
                            path.name,
                        file_type=
                            "docx",
                        section=
                            current_section,
                        metadata={
                            "source_type":
                                "docx"
                        }
                    )
                )

            current_parts = []

        def add_visual(
            relationship_id: str
        ):
            image_part = (
                document
                .part
                .related_parts
                .get(
                    relationship_id
                )
            )

            if image_part is None:
                return

            if not _is_useful_docx_image(
                image_part
            ):
                return

            blob = getattr(
                image_part,
                "blob",
                b""
            )

            digest = sha256(
                blob
            ).hexdigest()

            if digest in seen_images:
                return

            seen_images.add(
                digest
            )

            try:
                analysis = (
                    analyze_visual(
                        blob,
                        mime_type=
                            _image_mime_type(
                                image_part
                            ),
                        filename=
                            path.name,
                        section=
                            current_section
                    )
                )
            except Exception as error:
                print(
                    "Visual analysis skipped "
                    f"for {path.name}: "
                    f"{error}"
                )

                analysis = None

            if not analysis:
                return

            results.append(
                NormalizedContent(
                    content=
                        analysis[
                            "evidence_text"
                        ],
                    filename=
                        path.name,
                    file_type=
                        "docx",
                    section=
                        current_section,
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

        for block in iter_block_items(
            document
        ):
            if isinstance(
                block,
                Paragraph
            ):
                text = (
                    block.text
                    .strip()
                )

                style_name = (
                    block.style.name
                    if block.style
                    is not None
                    else ""
                )

                is_heading = (
                    bool(text)
                    and style_name
                    .lower()
                    .startswith(
                        "heading"
                    )
                )

                if is_heading:
                    flush_section()
                    current_section = (
                        text
                    )

                elif text:
                    current_parts.append(
                        text
                    )

                image_relationship_ids = (
                    _paragraph_image_relationship_ids(
                        block
                    )
                )

                if image_relationship_ids:
                    # Preserve document order: text accumulated
                    # before the visual becomes a text item first.
                    flush_section()

                    for relationship_id in (
                        image_relationship_ids
                    ):
                        add_visual(
                            relationship_id
                        )

            elif isinstance(
                block,
                Table
            ):
                table_lines = []

                for row in block.rows:
                    values = [
                        cell.text.strip()
                        for cell
                        in row.cells
                    ]

                    if any(values):
                        table_lines.append(
                            " | ".join(
                                values
                            )
                        )

                if table_lines:
                    current_parts.append(
                        "\n".join(
                            table_lines
                        )
                    )

        flush_section()

        if not results:
            raise ValueError(
                "The DOCX file does not contain "
                "any readable content."
            )

        return results