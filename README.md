# KnowledgeHub AI

A document-based Retrieval-Augmented Generation (RAG) application that allows users to upload PDF documents and ask questions about their contents.

KnowledgeHub AI processes uploaded documents, converts their content into searchable vector representations, retrieves relevant document chunks for a question, and uses an AI model to generate an answer grounded in the retrieved context.

## Features

* Upload PDF documents through the web interface
* Automatically extract text from uploaded PDFs
* Split documents into overlapping text chunks
* Generate vector embeddings for document chunks
* Store document chunks and embeddings in PostgreSQL with pgvector
* Perform similarity-based document retrieval
* Generate answers using retrieved document context
* Return source document, chunk, and relevance information with answers
* Maintain multiple chat sessions
* Load previous conversations from chat history
* Create and delete chat sessions
* View uploaded documents
* Delete documents and their indexed chunks
* Reject unsupported file types during upload
* Keep API credentials and local documents outside the public repository

## How It Works

```text
                 ┌─────────────────────┐
                 │     User uploads    │
                 │        PDF          │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │    Text Extraction │
                 │      PyMuPDF        │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   Text Chunking     │
                 │  1000 chars /       │
                 │  300 char overlap   │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Gemini Embeddings   │
                 │ embedding-001       │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ PostgreSQL +        │
                 │ pgvector            │
                 └──────────┬──────────┘
                            │
                    User asks question
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Embed the question  │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Vector similarity   │
                 │ search              │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Relevant document   │
                 │ chunks              │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Gemini generation   │
                 │ using retrieved     │
                 │ document context    │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Grounded answer +   │
                 │ source information  │
                 └─────────────────────┘
```

## RAG Pipeline

KnowledgeHub AI follows a basic retrieval-augmented generation pipeline:

### 1. Document ingestion

When a PDF is uploaded, the backend saves it to the local `documents` directory and sends it through the existing ingestion pipeline.

### 2. Text extraction

PDF text is extracted using PyMuPDF.

### 3. Chunking

The extracted text is divided into chunks of approximately 1000 characters with an overlap of 300 characters.

The overlap helps preserve context between adjacent chunks.

### 4. Embedding generation

Each chunk is converted into a vector embedding using Google's Gemini embedding model.

### 5. Vector storage

The document metadata, text chunks, and embeddings are stored in PostgreSQL.

The application uses pgvector similarity operations to retrieve the chunks most relevant to a user's question.

### 6. Retrieval

When a user asks a question, the question is also converted into an embedding.

The backend compares the question embedding against stored document embeddings and retrieves the closest matching chunks.

### 7. Answer generation

The retrieved chunks are supplied to Gemini as document context.

The generation prompt instructs the model to:

* Answer only from the supplied document context
* Avoid inventing information
* State when the requested information cannot be found
* Provide a clear and concise answer

### 8. Source attribution

The response includes source information such as:

* Document filename
* Chunk index
* Relevance score

This makes it possible to understand which parts of the knowledge base were used to generate the answer.

## Architecture

```text
Frontend
   │
   │ HTTP requests
   ▼
FastAPI Backend
   │
   ├── Document Management
   │      ├── Upload PDF
   │      ├── List Documents
   │      └── Delete Documents
   │
   ├── Chat Management
   │      ├── Create Chat
   │      ├── Load Chat
   │      ├── Delete Chat
   │      └── Store Messages
   │
   └── RAG Pipeline
          │
          ├── PDF Processing
          ├── Embedding Generation
          ├── Vector Search
          └── Answer Generation
                    │
                    ▼
              Gemini API

FastAPI Backend
       │
       ▼
PostgreSQL + pgvector
       │
       ├── Documents
       ├── Document Chunks
       ├── Embeddings
       ├── Chat Sessions
       └── Chat Messages
```

## Technology Stack

| Component                 | Technology            |
| ------------------------- | --------------------- |
| Frontend                  | HTML, CSS, JavaScript |
| Backend API               | FastAPI               |
| Language                  | Python                |
| Database                  | PostgreSQL            |
| Vector Search             | pgvector              |
| Embeddings                | Gemini Embeddings     |
| Generation                | Gemini                |
| PDF Processing            | PyMuPDF               |
| Database Driver           | psycopg               |
| Environment Configuration | python-dotenv         |

## Project Structure

```text
KnowledgeHub-AI/
│
├── backend/
│   ├── db.py
│   ├── embedding.py
│   ├── ingest.py
│   ├── main.py
│   ├── process_document.py
│   ├── rag.py
│   ├── search.py
│   ├── .gitignore
│   └── .env                  # Local only - not committed
│
├── documents/
│   └── .gitkeep              # Uploaded PDFs remain local
│
├── frontend/
│   └── index.html
│
├── tests/
│
├── .gitignore
└── README.md
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

### 1. Clone the repository

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

### 3. Configure environment variables

Create:

```text
backend/.env
```

and add the required Gemini and PostgreSQL configuration.

### 4. Start the backend

From the `backend` directory:

```bash
cd backend
uvicorn main:app --reload
```

The FastAPI backend will run locally on:

```text
http://127.0.0.1:8000
```

### 5. Open the frontend

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
8. KnowledgeHub retrieves relevant chunks.
9. Gemini generates an answer using those chunks.
10. The UI displays the answer together with source information.

## Current Limitations

* PDF is currently the supported upload format.
* Uploaded documents are stored locally and intentionally excluded from Git.
* API credentials are configured locally through environment variables.
* The current frontend is a lightweight HTML/CSS/JavaScript interface.
* Retrieval quality depends on the quality of document extraction, chunking, embeddings, and similarity threshold configuration.
* The current project does not yet include a production deployment configuration.

## Testing

The application has been manually tested during development for:

* PDF upload
* Document ingestion
* Document listing
* Document deletion
* Question answering
* Source display
* Chat creation
* Chat history
* Existing chat loading
* Chat deletion
* Unsupported file upload handling
* Frontend/backend communication
* Browser refresh behavior

## Security Notes

The repository intentionally excludes:

* API keys
* `.env` files
* Uploaded documents
* Python cache files
* Other local-only files

Never add credentials directly to the source code.

If an API key is accidentally committed to a public repository, revoke and replace the exposed credential immediately.

## Roadmap

Planned improvements include:

* Automated tests
* Dependency management
* Improved frontend experience
* Better error handling
* More robust retrieval evaluation
* Authentication and authorization
* Production deployment
* Containerization
* Observability and application monitoring
* Support for additional document formats
* Improved document and chat management
* CI/CD automation

## Project Status

**Current status: Working prototype / V1**

The core document ingestion, vector retrieval, RAG answering, document management, and chat history functionality is implemented and manually tested.

Future iterations will focus on reliability, evaluation, deployment, security, and production-readiness.

## Author

**Phaneendra Katakam**

GitHub: [@phaneendrakatakam](https://github.com/phaneendrakatakam)
