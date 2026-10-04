from pathlib import Path
import re

from .base import (
    BaseParser,
    NormalizedContent
)


class MarkdownParser(BaseParser):

    supported_extensions = (
        ".md",
        ".markdown"
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
                f"File not found: {file_path}"
            )

        try:
            content = path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            content = path.read_text(
                encoding="utf-8",
                errors="replace"
            )

        content = content.strip()

        if not content:
            raise ValueError(
                "The Markdown file does not contain "
                "any readable content."
            )

        lines = content.splitlines(
            keepends=True
        )

        results = []

        heading_stack: list[
            tuple[int, str]
        ] = []

        current_section: str | None = None
        current_lines: list[str] = []
        intro_lines: list[str] = []

        in_fence = False
        fence_marker = None

        heading_pattern = re.compile(
            r"^(#{1,6})\s+(.+?)\s*$"
        )

        def normalize_block(
            lines_to_join
        ) -> str:
            """
            Preserve internal formatting exactly while
            removing only leading/trailing blank space
            introduced by block boundaries.
            """

            return "".join(
                lines_to_join
            ).strip()

        def flush_intro():
            intro = normalize_block(
                intro_lines
            )

            if intro:
                results.append(
                    NormalizedContent(
                        content=intro,
                        filename=path.name,
                        file_type="markdown",
                        section=None,
                        metadata={
                            "source_type":
                                "markdown"
                        }
                    )
                )

            intro_lines.clear()

        def flush_section():
            nonlocal current_lines

            section_content = (
                normalize_block(
                    current_lines
                )
            )

            if section_content:
                results.append(
                    NormalizedContent(
                        content=
                            section_content,
                        filename=
                            path.name,
                        file_type=
                            "markdown",
                        section=
                            current_section,
                        metadata={
                            "source_type":
                                "markdown"
                        }
                    )
                )

            current_lines = []

        for line in lines:
            stripped = (
                line.strip()
            )

            if (
                stripped.startswith(
                    "```"
                )
                or stripped.startswith(
                    "~~~"
                )
            ):
                marker = (
                    stripped[:3]
                )

                if not in_fence:
                    in_fence = True
                    fence_marker = marker

                elif marker == fence_marker:
                    in_fence = False
                    fence_marker = None

                if current_lines:
                    current_lines.append(
                        line
                    )
                else:
                    intro_lines.append(
                        line
                    )

                continue

            heading_match = (
                None
                if in_fence
                else heading_pattern.match(
                    line.rstrip(
                        "\r\n"
                    )
                )
            )

            if heading_match:
                flush_intro()
                flush_section()

                level = len(
                    heading_match.group(1)
                )

                heading_text = (
                    heading_match.group(2)
                    .strip()
                )

                heading_stack = [
                    (
                        existing_level,
                        existing_text
                    )
                    for (
                        existing_level,
                        existing_text
                    )
                    in heading_stack
                    if existing_level < level
                ]

                heading_stack.append(
                    (
                        level,
                        heading_text
                    )
                )

                current_section = (
                    " > ".join(
                        text
                        for _, text
                        in heading_stack
                    )
                )

                current_lines = [
                    line
                ]

                continue

            if current_lines:
                current_lines.append(
                    line
                )
            else:
                intro_lines.append(
                    line
                )

        flush_intro()
        flush_section()

        if not results:
            results.append(
                NormalizedContent(
                    content=content,
                    filename=path.name,
                    file_type="markdown",
                    metadata={
                        "source_type":
                            "markdown"
                    }
                )
            )

        return results