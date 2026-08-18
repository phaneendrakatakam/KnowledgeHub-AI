# KnowledgeHub AI

A document-based Retrieval-Augmented Generation (RAG) application that allows users to upload PDF documents and ask questions about their contents.

KnowledgeHub AI processes uploaded documents, converts their content into searchable vector representations, retrieves relevant document chunks for a question, and uses an AI model to generate an answer grounded in the retrieved context.

## Features

- Upload PDF documents through the web interface
- Automatically extract text from uploaded PDFs
- Split documents into overlapping text chunks
- Generate vector embeddings for document chunks
- Store document chunks and embeddings in PostgreSQL with pgvector
- Perform similarity-based document retrieval
- Generate answers using retrieved document context
- Return source document, chunk, and relevance information with answers
- Maintain multiple chat sessions
- Load previous conversations from chat history
- Create and delete chat sessions
- View uploaded documents
- Delete documents and their indexed chunks
- Reject unsupported file types during upload
- Return grounded fallback responses when relevant information is not available
- Keep API credentials and local documents outside the public repository
- Automated testing of core document processing, retrieval, and RAG functionality

### KnowledgeHub AI Interface

The V1 web interface provides document management, chat history, PDF upload, and document question-answering functionality.

![KnowledgeHub AI Interface](screenshots/KnowledgeHub%20AI.png)

### PDF Upload and Ingestion

PDF documents can be uploaded through the web interface and automatically processed into the knowledge base.

![Successful PDF Ingestion](screenshots/Successful%20PDF%20ingestion.png)

### RAG Question Answering

KnowledgeHub retrieves relevant document chunks and generates an answer grounded in the retrieved context.

Each answer can include the source document, chunk index, and relevance score used during retrieval.

![RAG Question Answering](screenshots/Continuous%20Delivery%20vs%20Deployment.png)

### Grounded Response

KnowledgeHub is designed to avoid answering questions when sufficiently relevant information cannot be found in the provided documents.

![Grounded Response](screenshots/CEO%20of%20Microsoft%20rejection.png)

### Automated Testing

Core document processing, retrieval, and RAG functionality is covered by automated tests using pytest.

![Automated Tests](screenshots/16%20passed.png)

**V1 automated test result: 16/16 passed.**

## How It Works

```text
+----------------------+
|      User Uploads    |
|         PDF          |
+----------+-----------+
           |
           v
+----------------------+
|   Text Extraction    |
|      PyMuPDF         |
+----------+-----------+
           |
           v
+----------------------+
|    Text Chunking     |
| 1000 chars / 300     |
|    char overlap      |
+----------+-----------+
           |
           v
+----------------------+
| Gemini Embeddings    |
| embedding-001        |
+----------+-----------+
           |
           v
+----------------------+
| PostgreSQL + pgvector|
|                      |
| Documents            |
| Chunks               |
| Embeddings           |
+----------+-----------+
           |
           | User asks question
           v
+----------------------+
| Embed the Question   |
+----------+-----------+
           |
           v
+----------------------+
| Vector Similarity    |
|       Search         |
+----------+-----------+
           |
           v
+----------------------+
| Relevant Document    |
|       Chunks         |
+----------+-----------+
           |
           v
+----------------------+
| Gemini Generation    |
| Using Retrieved      |
| Document Context     |
+----------+-----------+
           |
           v
+----------------------+
| Grounded Answer +    |
| Source Information   |
+----------------------+
```

## RAG Pipeline

KnowledgeHub AI follows a retrieval-augmented generation pipeline.

### 1. Document Ingestion

When a PDF is uploaded, the backend saves it to the local `documents` directory and sends it through the document ingestion pipeline.

### 2. Text Extraction

PDF text is extracted using PyMuPDF.

### 3. Chunking

The extracted text is divided into chunks of approximately 1000 characters with an overlap of 300 characters.

The overlap helps preserve context between adjacent chunks.

### 4. Embedding Generation

Each document chunk is converted into a vector embedding using Google's Gemini embedding model.

### 5. Vector Storage

Document metadata, text chunks, and embeddings are stored in PostgreSQL.

The application uses pgvector similarity operations to retrieve chunks that are most relevant to a user's question.

### 6. Retrieval

When a user asks a question, the question is also converted into an embedding.

The backend compares the question embedding against stored document embeddings and retrieves the closest matching chunks.

A relevance threshold is applied so that insufficiently relevant results can be rejected instead of being supplied to the generation model.

### 7. Answer Generation

The retrieved chunks are supplied to Gemini as document context.

The generation prompt instructs the model to:

- Answer only from the supplied document context
- Avoid inventing or assuming information
- State when the requested information cannot be found
- Provide a clear and concise answer

### 8. Source Attribution

The response includes source information such as:

- Document filename
- Chunk index
- Relevance score

This makes it possible to understand which parts of the knowledge base were used to generate the answer.

## Architecture

```text
                         +------------------+
                         |     Frontend     |
                         |   HTML/CSS/JS    |
                         +--------+---------+
                                  |
                                  | HTTP Requests
                                  v
                         +------------------+
                         |   FastAPI API    |
                         |     Backend      |
                         +--------+---------+
                                  |
                +-----------------+-----------------+
                |                 |                 |
                v                 v                 v
       +----------------+ +----------------+ +----------------+
       |    Document    | |      Chat      | |      RAG       |
       |   Management   | |   Management   | |    Pipeline    |
       +-------+--------+ +-------+--------+ +-------+--------+
               |                  |                  |
               v                  v                  v
       +----------------+ +----------------+ +----------------+
       | Upload PDF     | | Create Chat    | | PDF Processing |
       | List Documents | | Load Chat      | | Embeddings     |
       | Delete Document| | Delete Chat    | | Vector Search  |
       +----------------+ | Store Messages | | Generation     |
                          +----------------+ +-------+--------+
                                                    |
                              +---------------------+---------------------+
                              |                                           |
                              v                                           v
                     +------------------+                        +------------------+
                     | PostgreSQL       |                        |    Gemini API    |
                     | + pgvector       |                        +------------------+
                     +------------------+
```

## Technology Stack

| Component | Technology |
| --- | --- |
| Frontend | HTML, CSS, JavaScript |
| Backend API | FastAPI |
| Language | Python |
| Database | PostgreSQL |
| Vector Search | pgvector |
| Embeddings | Gemini Embeddings |
| Generation | Gemini |
| PDF Processing | PyMuPDF |
| Database Driver | psycopg |
| Environment Configuration | python-dotenv |
| Testing | pytest |

## Project Structure

```text
KnowledgeHub-AI/
|
+-- backend/
|   |
|   +-- db.py
|   +-- embedding.py
|   +-- ingest.py
|   +-- main.py
|   +-- process_document.py
|   +-- rag.py
|   +-- search.py
|   +-- .gitignore
|   +-- .env                  # Local only - not committed
|   +-- __pycache__/          # Local only - not committed
|
+-- documents/
|   +-- .gitkeep              # Directory placeholder
|   +-- Uploaded PDFs         # Local only - not committed
|
+-- frontend/
|   +-- index.html
|
+-- tests/
|   +-- test_process_document.py
|   +-- test_rag.py
|   +-- test_search.py
|
+-- screenshots/
|   +-- KnowledgeHub AI.png
|   +-- Successful PDF ingestion.png
|   +-- Continuous Delivery vs Deployment.png
|   +-- CEO of Microsoft rejection.png
|   +-- 16 passed.png
|
+-- .gitignore
+-- README.md
```

## Environment Variables

The backend uses environment variables for configuration.

Create a local file:

```text
backend/.env
```

Example:

```env
GEMINI_API_KEY=your_gemini_api_key

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=knowledgehub
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
```

**Do not commit the `.env` file or real API credentials to GitHub.**

The repository's `.gitignore` files are configured to keep local credentials, Python cache files, and uploaded documents out of version control.

## Running Locally

### 1. Clone the Repository

```bash
git clone https://github.com/phaneendrakatakam/KnowledgeHub-AI.git
cd KnowledgeHub-AI
```

### 2. Configure PostgreSQL

Create a PostgreSQL database named:

```text
knowledgehub
```

The database must also have the pgvector extension available because document embeddings are stored and queried as vectors.

### 3. Configure Environment Variables

Create:

```text
backend/.env
```

and add the required Gemini and PostgreSQL configuration.

### 4. Start the Backend

From the `backend` directory:

```bash
cd backend
python -m uvicorn main:app --reload
```

The FastAPI backend will run locally on:

```text
http://127.0.0.1:8000
```

### 5. Open the Frontend

Open:

```text
frontend/index.html
```

in a browser.

The frontend communicates with the FastAPI backend and provides the document upload, document management, chat history, and question-answering interface.

## API Endpoints

### Health Check

```http
GET /
```

Returns a message confirming that the KnowledgeHub AI backend is running.

### Document Upload

```http
POST /documents/upload
```

Uploads and ingests a PDF document.

### List Documents

```http
GET /documents
```

Returns the documents currently registered in the knowledge base.

### Delete Document

```http
DELETE /documents/{document_id}
```

Deletes the document and its associated indexed chunks.

### Create Chat

```http
POST /chats
```

Creates a new chat session.

### List Chats

```http
GET /chats
```

Returns the available chat sessions.

### Ask a Question

```http
POST /ask
```

Processes a question through the retrieval and generation pipeline.

### Load Chat

```http
GET /chats/{session_id}
```

Loads the messages belonging to a chat session.

### Delete Chat

```http
DELETE /chats/{session_id}
```

Deletes a chat session and its stored messages.

## Example Workflow

1. Start PostgreSQL with pgvector enabled.
2. Configure the local `.env` file.
3. Start the FastAPI backend.
4. Open the frontend.
5. Upload a PDF.
6. Wait for document ingestion to complete.
7. Ask a question about the uploaded document.
8. KnowledgeHub embeds the question and retrieves relevant document chunks.
9. Retrieved chunks that meet the relevance threshold are supplied to Gemini.
10. Gemini generates an answer using the retrieved document context.
11. The UI displays the answer together with source and relevance information.

## Testing

KnowledgeHub AI V1 includes both manual functional testing and automated unit testing.

### Automated Testing

The V1 automated test suite contains **16 tests** covering the core document-processing, retrieval, and RAG functionality.

The test suite covers areas including:

- Empty and whitespace-only document handling
- PDF text extraction
- Document chunk creation
- Chunk size and overlap behavior
- Document processing
- Embedding flow using mocks
- Search result handling
- Custom search limits
- Empty search results
- RAG fallback behavior
- Relevance filtering
- Prompt and document-context construction
- Source attribution
- Multiple relevant sources

External dependencies are mocked where appropriate so application logic can be tested without making unnecessary Gemini API or database calls.

Run the complete test suite from the project root:

```bash
python -m pytest -v
```

Current V1 result:

```text
16 passed
```

### Manual Testing

The application has also been manually tested for:

- PDF upload
- Document ingestion
- Document listing
- Document deletion
- Question answering
- Source and relevance display
- Chat creation
- Chat history
- Existing chat loading
- Chat deletion
- Unsupported file upload handling
- Frontend/backend communication
- Browser refresh behavior
- Grounded fallback behavior for questions not supported by the uploaded documents

## Security Notes

The repository intentionally excludes:

- API keys
- `.env` files
- Uploaded documents
- Python cache files
- Other local-only files

Never add credentials directly to the source code.

If an API key is accidentally committed to a public repository, revoke and replace the exposed credential immediately.

## Current Limitations

- PDF is currently the supported upload format.
- Uploaded documents are stored locally and intentionally excluded from Git.
- API credentials are configured locally through environment variables.
- The current frontend is a lightweight HTML/CSS/JavaScript interface.
- Retrieval quality depends on document extraction, chunking, embeddings, and similarity configuration.
- The application currently runs locally and does not include a production deployment configuration.
- Markdown returned by the generation model is currently displayed as plain text by the frontend.

## V2 Roadmap

Potential V2 improvements include:

- Dependency management
- Improved frontend experience
- Markdown rendering for generated answers
- Better error handling
- More robust retrieval evaluation
- Improved retrieval and chunking strategies
- Conversation-aware retrieval
- Authentication and authorization
- Support for additional document formats
- Improved document and chat management
- Expanded automated test coverage

Longer-term improvements include containerization, observability, CI/CD automation, and production deployment.

## Project Status

**KnowledgeHub AI V1 — Complete ✅**

V1 includes:

- PDF ingestion and text extraction
- Overlapping document chunking
- Gemini vector embeddings
- PostgreSQL + pgvector storage
- Semantic similarity search
- Retrieval-Augmented Generation
- Relevance filtering
- Grounded answer generation
- Source attribution with chunk and relevance information
- Document management
- Multiple chat sessions and chat history
- Manual functional testing
- Automated unit testing

**Automated test suite: 16/16 passed.**

V1 is feature-complete and serves as the stable foundation for future KnowledgeHub AI versions.

## Author

**Phaneendra Katakam**

GitHub: [@phaneendrakatakam](https://github.com/phaneendrakatakam)