# C-OCR Quick Start Guide

Complete guide to get the C-OCR platform running locally.

## Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **PostgreSQL 13+**
- **Redis 6+**

## Quick Start (Development)

### 1. Start Infrastructure Services

Using Docker Compose (recommended):
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis
```

Or install and start them manually on your system.

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example .env

# Edit .env and configure:
# - DATABASE_URL
# - REDIS_URL
# - SECRET_KEY (generate with: openssl rand -hex 32)

# Run database migrations
alembic upgrade head

# Seed database with default users
python scripts/seed_database.py

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

### 3. Start Celery Worker (New Terminal)

```bash
cd backend
venv\Scripts\activate  # or source venv/bin/activate

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

Note: On Windows, use `--pool=solo` flag.

### 4. Frontend Setup (New Terminal)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## Access the Application

1. Open browser: http://localhost:3000
2. Login with default credentials:
   - **Admin**: admin@c-ocr.local / admin123
   - **Operator**: operator@c-ocr.local / operator123
   - **Reviewer**: reviewer@c-ocr.local / reviewer123

## Verify Installation

### Test Backend API
```bash
curl http://localhost:8000/api/v1/health
```

### Test Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@c-ocr.local&password=admin123"
```

### Upload a Test Document
1. Login to the web UI
2. Navigate to "Documents"
3. Drag and drop a PDF or image file
4. Select document category
5. Watch the processing status

## Production Build

### Backend
```bash
cd backend
pip install -r requirements.txt
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend
```bash
cd frontend
npm run build
# Serve the dist/ folder with nginx or any static file server
```

### Using Docker Compose (Full Stack)
```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'app'"
**Solution**: Ensure you're in the backend directory and virtual environment is activated.

### Issue: "Cannot connect to PostgreSQL"
**Solution**:
- Check PostgreSQL is running: `docker-compose ps`
- Verify DATABASE_URL in .env file
- Check credentials and port (default: 5432)

### Issue: "Cannot connect to Redis"
**Solution**:
- Check Redis is running: `docker-compose ps`
- Verify REDIS_URL in .env file (default: redis://localhost:6379/0)

### Issue: "Frontend shows 'Network Error'"
**Solution**:
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify VITE_API_BASE_URL in frontend/.env

### Issue: "Celery worker not processing documents"
**Solution**:
- Check Celery worker logs for errors
- Verify Redis connection
- Ensure storage directory has write permissions
- Check celery worker is running: `ps aux | grep celery`

## File Storage

By default, files are stored in:
```
backend/storage/
└── tenants/
    └── {tenant_id}/
        ├── documents/
        ├── ocr_results/
        └── searchable_pdfs/
```

For production, configure S3-compatible storage in .env:
```env
STORAGE_BACKEND=s3
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

## Database Management

### Create new migration
```bash
cd backend
alembic revision --autogenerate -m "description"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

## Monitoring

### Check Celery tasks
```bash
# In Python shell
from app.workers.celery_app import celery_app
inspect = celery_app.control.inspect()
inspect.active()      # Active tasks
inspect.scheduled()   # Scheduled tasks
inspect.stats()       # Worker stats
```

### Database queries
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U cocr_user -d cocr_db

# Useful queries
SELECT * FROM documents ORDER BY created_at DESC LIMIT 10;
SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 20;
SELECT COUNT(*) FROM ocr_pages;
```

## Next Steps

1. **Create Templates**: Navigate to Templates page and create your first extraction template
2. **Upload Documents**: Test with sample documents in your category
3. **Review Results**: Check extraction results and adjust templates as needed
4. **Generate API Keys**: Create API keys for external integrations
5. **Configure Users**: Add team members with appropriate roles

## Support

- **Documentation**: See [README.md](README.md) and [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- **API Reference**: http://localhost:8000/docs (when backend is running)
- **Postman Collection**: [docs/C-OCR-API.postman_collection.json](docs/C-OCR-API.postman_collection.json)

## Security Notes

For production deployment:
- Change all default passwords
- Generate secure SECRET_KEY and API_KEY_HASH_SALT
- Enable HTTPS/TLS
- Configure firewall rules
- Set up database backups
- Review and adjust rate limiting
- Enable audit logging monitoring
- Use environment-specific .env files
