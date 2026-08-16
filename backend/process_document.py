import fitz

from embedding import create_embedding


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 300


def extract_text(file_path):
    document = fitz.open(file_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


def create_chunks(text):
    chunks = []

    step = CHUNK_SIZE - CHUNK_OVERLAP

    for start in range(0, len(text), step):

        chunk = text[start:start + CHUNK_SIZE]

        if not chunk.strip():
            continue

        chunks.append(chunk)

        if start + CHUNK_SIZE >= len(text):
            break

    return chunks


def process_document(file_path):
    text = extract_text(file_path)

    chunks = create_chunks(text)

    results = []

    for index, chunk in enumerate(chunks):

        embedding = create_embedding(chunk)

        results.append({
            "chunk_id": index,
            "text": chunk,
            "embedding": embedding
        })

    return results