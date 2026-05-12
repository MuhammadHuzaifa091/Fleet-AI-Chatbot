# Fleet Intelligence RAG Platform

An enterprise-grade AI-powered Fleet Intelligence system using Python FastAPI and Traccar MySQL database.

## Features
- **Retrieval-Augmented Generation (RAG)**: Combines live SQL telemetry with semantic vector search.
- **Intent Routing**: Automatically routes queries to SQL retrievers, semantic search, or analytics agents.
- **Proactive Analytics**: Idle analysis, overspeeding trends, and maintenance alerts.
- **Conversational Memory**: Redis-backed session memory for follow-up questions.
- **High Performance**: Fully asynchronous architecture using FastAPI and SQLAlchemy.

## Tech Stack
- **API**: FastAPI (Python 3.12)
- **Database**: MySQL (Traccar)
- **Vector Search**: Qdrant
- **LLM**: DeepSeek
- **Embeddings**: Sentence Transformers
- **Cache**: Redis

## Setup Instructions

### 1. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
- `DEEPSEEK_API_KEY`: Get from [DeepSeek API](https://platform.deepseek.com/)
- `DB_*`: Your Traccar MySQL credentials (pre-filled for this demo)

### 2. Docker Deployment
```bash
docker-compose up --build
```

### 3. API Documentation
Once running, visit:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4. Initialization
After starting the system, reindex the fleet data to enable semantic search:
```bash
curl -X POST http://localhost:8000/api/v1/embeddings/reindex
```

## API Endpoints

### Chat
`POST /api/v1/chat/`
```json
{
  "query": "Show vehicle ABC and what is its fuel status?",
  "session_id": "user-session-123"
}
```

### Live Vehicles
`GET /api/v1/vehicles/live`

### Telemetry
`GET /api/v1/telemetry/overspeeding?days=7`
`GET /api/v1/telemetry/maintenance`

## Architecture
The system follows a clean modular architecture:
- `app/api`: API route definitions.
- `app/rag`: Core RAG logic and intent routing.
- `app/retrievers`: Data fetching logic (SQL/Vector).
- `app/llm`: DeepSeek integration.
- `app/memory`: Redis session management.
- `app/models`: Database schema definitions.
