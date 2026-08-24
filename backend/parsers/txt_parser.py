from pathlib import Path

from .base import (
    BaseParser,
    NormalizedContent
)


class TextParser(BaseParser):

    supported_extensions = (
        ".txt",
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


        content = (
            content
            .strip()
        )


        if not content:

            raise ValueError(
                "The text file does not contain "
                "any readable content."
            )


        return [

            NormalizedContent(

                content=
                    content,

                filename=
                    path.name,

                file_type=
                    "txt",

                metadata={
                    "source_type":
                        "text"
                }

            )

        ]