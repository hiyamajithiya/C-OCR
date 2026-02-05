# C-OCR: OCR + Template-based Data Extraction Platform

Production-ready OCR and template-based data extraction platform designed for Chartered Accountant (CA) offices.

## Features

- **OCR Processing**: Support for scanned PDFs and images (JPG/PNG/TIFF) using PaddleOCR and Tesseract
- **Template-based Extraction**: Train once, reuse for similar document formats
- **Searchable PDF Generation**: Maintain original document appearance with OCR text layer
- **Multi-tenant Architecture**: Isolated data and templates per tenant
- **RESTful API**: Secure API with API key authentication
- **Role-based Access Control**: Admin, Operator, and Reviewer roles
- **Audit Logging**: Complete activity tracking
- **Async Processing**: Celery-based queue for scalable document processing

## Architecture

### Technology Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL (Database)
- Redis (Cache & Message Broker)
- Celery (Async Task Queue)
- PaddleOCR / Tesseract (OCR Engines)
- PyMuPDF / pdfplumber (PDF Processing)
- OpenCV + Pillow (Image Processing)

**Frontend (Coming Soon):**
- React + TypeScript
- Material-UI / Ant Design

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd C-OCR
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and update the configuration values, especially:
   - `JWT_SECRET`
   - `API_KEY_HASH_SALT`
   - Database credentials (if changed)

3. **Start services with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL database (port 5432)
   - Redis (port 6379)
   - FastAPI backend (port 8000)
   - Celery worker

4. **Initialize the database:**
   ```bash
   # Wait for services to be healthy
   docker-compose ps

   # Run database seed script
   python scripts/seed_database.py
   ```

   This creates:
   - Default tenant
   - Admin user (`admin@c-ocr.local` / `admin123`)
   - Operator user (`operator@c-ocr.local` / `operator123`)
   - Reviewer user (`reviewer@c-ocr.local` / `reviewer123`)
   - Default API key (displayed once)

5. **Access the application:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs
   - Health Check: http://localhost:8000/health

## API Usage

### Authentication

#### User Login (JWT)
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@c-ocr.local&password=admin123"
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@c-ocr.local",
    "name": "Admin User",
    "role": "admin"
  }
}
```

#### API Key Authentication
```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@invoice.pdf"
```

### Document Upload

```bash
# Using JWT
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf" \
  -F "doc_category=invoice"
```

### Get Document Status

```bash
curl -X GET http://localhost:8000/api/v1/documents/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Extraction Results

```bash
curl -X GET http://localhost:8000/api/v1/documents/1/result \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Download Searchable PDF

```bash
curl -X GET "http://localhost:8000/api/v1/documents/1/download?kind=searchable_pdf" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o output.pdf
```

## Development

### Local Development Setup

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL and Redis:**
   ```bash
   docker-compose up postgres redis -d
   ```

3. **Run database migrations:**
   ```bash
   cd backend
   alembic upgrade head
   ```

4. **Run the API server:**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Run Celery worker (in separate terminal):**
   ```bash
   cd backend
   celery -A app.workers.celery_app worker --loglevel=info
   ```

### Project Structure

```
C-OCR/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   │   ├── endpoints/    # Route handlers
│   │   │   └── dependencies/ # Auth & dependencies
│   │   ├── core/             # Config, database, security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Business logic
│   │   ├── workers/          # Celery tasks
│   │   └── utils/            # Utility functions
│   ├── alembic/              # Database migrations
│   ├── tests/                # Test files
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile
├── frontend/                 # React frontend (coming soon)
├── docker/                   # Docker configs
├── scripts/                  # Utility scripts
│   └── seed_database.py      # Database seeding
├── docs/                     # Documentation
├── docker-compose.yml
├── .env.example
└── README.md
```

## Database Schema

### Main Tables

- **tenants**: Multi-tenant isolation
- **users**: User accounts with RBAC
- **api_keys**: API key management
- **documents**: Uploaded documents
- **document_files**: Associated files (original, processed, exports)
- **ocr_pages**: OCR results per page
- **templates**: Document format definitions
- **template_versions**: Template configurations with versioning
- **extraction_jobs**: Async processing jobs
- **extraction_results**: Extracted data
- **audit_logs**: Complete activity audit trail

## User Roles

- **Admin**: Full access - manage users, templates, API keys, settings
- **Operator**: Upload documents, view results, request training
- **Reviewer**: Approve templates and extraction outputs

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/c_ocr
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/c_ocr

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Security
JWT_SECRET=your-secret-key-change-in-production
API_KEY_HASH_SALT=your-salt-change-in-production

# OCR
OCR_ENGINE_PRIMARY=paddle  # paddle or tesseract
OCR_LANGS=en
DEFAULT_DPI=300

# Template Matching
TEMPLATE_MATCH_THRESHOLD=0.75
```

## Testing

Run tests:
```bash
cd backend
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## Deployment

### Production Checklist

1. ✓ Change all default passwords
2. ✓ Generate strong JWT_SECRET and API_KEY_HASH_SALT
3. ✓ Enable HTTPS/TLS
4. ✓ Configure proper CORS origins
5. ✓ Set up file storage backup
6. ✓ Configure log aggregation
7. ✓ Set up monitoring and alerting
8. ✓ Review rate limits and quotas
9. ✓ Enable database backups
10. ✓ Review security settings

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f api worker

# Stop all services
docker-compose down

# Stop and remove volumes (caution: data loss)
docker-compose down -v
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Support

For issues, questions, or contributions, please refer to the project repository.

## License

[Specify License]

## Security

- API keys are hashed using SHA-256 with salt
- Passwords are hashed using bcrypt
- JWT tokens for session management
- Role-based access control (RBAC)
- Complete audit logging
- TLS/HTTPS support

## Roadmap

- [ ] Frontend UI implementation
- [ ] Advanced AI extraction (optional module)
- [ ] Support for Indian languages (Hindi/Gujarati)
- [ ] S3/Minio storage adapter
- [ ] HTML/DOCX export
- [ ] Batch processing API
- [ ] Desktop application wrapper
