# Real Estate Voice AI Agent

Outbound voice AI agent for real estate lead qualification in India using Exotel, Deepgram STT, GPT-4o-mini, and ElevenLabs TTS.

## Project Status

**Current Module: Module 1 - Core Infrastructure** ✅

- [x] Project structure and dependencies
- [x] Configuration management
- [x] Database models (Lead, CallSession, Conversation)
- [x] Database and Redis connections
- [x] Logging infrastructure
- [x] FastAPI server with health checks
- [ ] Module 2: Campaign Management & CSV Upload
- [ ] Module 3: Exotel Integration
- [ ] Module 4: Speech-to-Text (Deepgram)
- [ ] Module 5: Conversation Engine (GPT-4o-mini)
- [ ] Module 6: Text-to-Speech (ElevenLabs)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Campaign   │  │   Exotel     │  │  WebSocket   │      │
│  │  Management  │  │  Integration │  │   Handler    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Deepgram   │  │  GPT-4o-mini │  │ ElevenLabs   │      │
│  │     STT      │  │ Conversation │  │     TTS      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐                    ┌──────────────┐      │
│  │  PostgreSQL  │                    │    Redis     │      │
│  │   Database   │                    │   Session    │      │
│  └──────────────┘                    └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Web Framework**: FastAPI
- **Database**: PostgreSQL (with SQLAlchemy async)
- **Cache/Session Store**: Redis
- **Telephony**: Exotel (Indian provider)
- **Speech-to-Text**: Deepgram
- **LLM**: OpenAI GPT-4o-mini
- **Text-to-Speech**: ElevenLabs

## Project Structure

```
voice-ai-real-estate/
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── config/
│   │   └── settings.py            # Environment configuration
│   ├── models/
│   │   ├── lead.py                # Lead data model
│   │   ├── call_session.py        # Call session model
│   │   └── conversation.py        # Conversation state model
│   ├── database/
│   │   ├── connection.py          # DB connection setup
│   │   └── repositories/          # Data access layer
│   ├── utils/
│   │   └── logger.py              # Structured logging
│   └── api/
│       └── health.py              # Health check endpoints
├── tests/
│   └── test_infrastructure.py
├── .env
├── .env.example
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (or use Docker)
- Redis (or use Docker)

### Step 1: Clone and Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env and fill in your credentials
# For Module 1, only DATABASE_URL and REDIS_URL are required
```

### Step 3: Start Database Services

```bash
# Start PostgreSQL and Redis using Docker Compose
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Step 4: Run the Application

```bash
# Run the FastAPI application
uvicorn src.main:app --reload

# Or using Python directly
python -m src.main
```

The application will start on `http://localhost:8000`

### Step 5: Verify Installation

Visit the following endpoints:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Readiness Check**: http://localhost:8000/health/ready
- **Liveness Check**: http://localhost:8000/health/live

All health checks should return `200 OK`.

## Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_infrastructure.py
```

## Database Models

### Lead Model
Stores lead information from CSV uploads:
- Contact details (name, phone, email)
- Property preferences (type, location, budget)
- Campaign tracking
- Call attempt history

### CallSession Model
Tracks individual call attempts:
- Call identifiers (call_sid, lead_id)
- Call status and outcome
- Full transcript and collected data
- Recording URL
- Duration and timestamps

### ConversationSession Model (In-Memory)
Active call state stored in Redis:
- Conversation stage tracking
- Real-time transcript history
- Collected information
- Audio buffers
- State flags and metrics

## API Endpoints

### Health Checks
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness probe (checks DB + Redis)
- `GET /health/live` - Liveness probe

### Root
- `GET /` - Service information

## Configuration

All configuration is managed through environment variables in `.env`:

### Application Settings
- `APP_NAME`: Application name
- `ENVIRONMENT`: development/staging/production
- `DEBUG`: Enable debug mode
- `LOG_LEVEL`: Logging level

### Database
- `DATABASE_URL`: PostgreSQL connection string

### Redis
- `REDIS_URL`: Redis connection string

### Call Settings
- `MAX_CALL_DURATION_MINUTES`: Maximum call duration
- `CALLING_HOURS_START`: Start time for calling (24h format)
- `CALLING_HOURS_END`: End time for calling (24h format)
- `MAX_CONCURRENT_CALLS`: Maximum concurrent calls

## Logging

The application uses structured logging:

- **Development**: Human-readable console logs
- **Production**: JSON-formatted logs for aggregation

Example log entry:
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "message": "Call initiated",
  "module": "call_handler",
  "call_sid": "abc123",
  "lead_id": 456
}
```

## Development

### Running in Development Mode

```bash
# Enable auto-reload
uvicorn src.main:app --reload --log-level debug

# Or set in .env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Database Migrations (Future)

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Module 1 Success Criteria

- [x] FastAPI server starts without errors
- [ ] Health check endpoint returns 200
- [ ] Readiness check verifies DB and Redis
- [ ] Database tables created successfully
- [ ] Settings load from .env
- [ ] All models import without errors
- [ ] Logging works correctly
- [ ] Can create Lead and ConversationSession objects

## Next Steps

Once Module 1 is complete and all tests pass:

1. **Module 2**: Campaign Management & CSV Upload
2. **Module 3**: Exotel Integration & Call Initiation
3. **Module 4**: Deepgram Speech-to-Text Integration
4. **Module 5**: GPT-4o-mini Conversation Engine
5. **Module 6**: ElevenLabs Text-to-Speech Integration
6. **Module 7**: End-to-End Testing & Optimization

## Troubleshooting

### Database Connection Error
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres
```

### Redis Connection Error
```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
redis-cli ping
```

### Port Already in Use
```bash
# Change PORT in .env
PORT=8001
```

## License

Proprietary - Internal Use Only

## Support

For issues and questions, contact the development team.
