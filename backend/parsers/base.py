from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class NormalizedContent:
    """
    Common representation produced by every KnowledgeHub
    document parser.

    The downstream ingestion pipeline should work with this
    structure instead of needing to know whether the original
    source was PDF, DOCX, TXT, Markdown, CSV or XLSX.
    """

    content: str

    filename: str

    file_type: str

    page_number: Optional[int] = None

    section: Optional[str] = None

    sheet_name: Optional[str] = None

    row_start: Optional[int] = None

    row_end: Optional[int] = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class BaseParser:
    """
    Base interface for all KnowledgeHub document parsers.
    """

    supported_extensions: tuple[str, ...] = tuple()

    def supports(
        self,
        filename: str
    ) -> bool:

        lowercase_name = (
            filename
            .lower()
        )

        return any(
            lowercase_name.endswith(
                extension
            )
            for extension
            in self.supported_extensions
        )

    def parse(
        self,
        file_path: str
    ) -> list[NormalizedContent]:

        raise NotImplementedError(
            "Parser must implement parse()."
        )