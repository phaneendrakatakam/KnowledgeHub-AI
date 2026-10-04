from embedding import create_embedding

from parsers import parse_document

from parsers.pdf_parser import PDFParser


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 300


def extract_text(
    file_path: str
):
    """
    Backward-compatible PDF text extraction helper.

    This function is retained because existing V1/V2
    tests and code may still rely on it.

    New V3 ingestion should use the parser architecture
    through parse_document().
    """

    parser = PDFParser()

    normalized_items = parser.parse(
        file_path
    )

    return "\n".join(
        item.content
        for item in normalized_items
    )


def create_chunks(
    text: str
):
    """
    Split normalized text into overlapping chunks.

    Chunking is independent of the original file type.
    """

    chunks = []

    step = (
        CHUNK_SIZE
        - CHUNK_OVERLAP
    )


    for start in range(
        0,
        len(text),
        step
    ):

        chunk = text[
            start:
            start + CHUNK_SIZE
        ]


        if not chunk.strip():
            continue


        chunks.append(
            chunk
        )


        if (
            start + CHUNK_SIZE
            >= len(text)
        ):
            break


    return chunks


def process_document(
    file_path: str
):
    """
    Parse a supported document, normalize its content,
    create chunks, and generate embeddings.

    The parser registry determines how the original
    document should be read.
    """

    normalized_items = (
        parse_document(
            file_path
        )
    )


    results = []

    chunk_index = 0


    for item in normalized_items:

        chunks = create_chunks(
            item.content
        )


        for chunk in chunks:

            embedding = (
                create_embedding(
                    chunk
                )
            )


            results.append({

                "chunk_id":
                    chunk_index,

                "text":
                    chunk,

                "embedding":
                    embedding,

                "filename":
                    item.filename,

                "file_type":
                    item.file_type,

                "page_number":
                    item.page_number,

                "section":
                    item.section,

                "sheet_name":
                    item.sheet_name,

                "row_start":
                    item.row_start,

                "row_end":
                    item.row_end,

                "metadata":
                    item.metadata,

            })


            chunk_index += 1


    return results