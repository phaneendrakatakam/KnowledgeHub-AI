from pathlib import Path

from .base import BaseParser, NormalizedContent
from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .txt_parser import TextParser
from .markdown_parser import MarkdownParser


PARSERS = [
    PDFParser(),
    DOCXParser(),
    TextParser(),
    MarkdownParser(),
]


def get_parser(filename: str) -> BaseParser:
    """Return the parser capable of handling the supplied filename."""
    for parser in PARSERS:
        if parser.supports(filename):
            return parser

    raise ValueError(
        f"Unsupported file type: {filename}"
    )


def parse_document(file_path: str) -> list[NormalizedContent]:
    """Select the correct parser and return normalized document content."""
    path = Path(file_path)
    parser = get_parser(path.name)
    return parser.parse(str(path))