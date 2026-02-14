# Geo2 IP Webserver

Multi-site webserver with geo and IP-based access control.

## Features

- **Multi-site hosting**: Create and manage multiple sites with unique hostnames
- **Per-site access control**: 
  - IP-only filtering
  - Geo-only filtering (GPS coordinates)
  - IP + Geo combined filtering
  - Disabled (no filtering)
- **Geofence support**: Circle (center + radius) or polygon
- **IP rules**: Allow/deny with CIDR notation
- **Admin UI**: React-based dashboard for site management
- **Audit logs**: Searchable logs with CSV export
- **Screenshot artifacts**: Capture screenshots of blocked access attempts

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL + PostGIS
- **Frontend**: React + TypeScript + Vite
- **Caching**: Redis
- **Storage**: MinIO / S3 for artifacts
- **Auth**: JWT

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Development with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:
- **Frontend**: http://localhost:3002
- **Backend API**: http://localhost:8002
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **MinIO Console**: http://localhost:9001

### Local Development

#### Backend

```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

#### Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --host 0.0.0.0 --port 3002
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `GET /api/auth/me` - Get current user

### Sites (Admin)
- `GET /api/admin/sites` - List sites
- `POST /api/admin/sites` - Create site
- `GET /api/admin/sites/{id}` - Get site
- `PUT /api/admin/sites/{id}` - Update site
- `DELETE /api/admin/sites/{id}` - Delete site
- `PUT /api/admin/sites/{id}/filter` - Update filter config

### Geofences
- `GET /api/admin/sites/{site_id}/geofences` - List geofences
- `POST /api/admin/sites/{site_id}/geofences` - Create geofence
- `PUT /api/admin/sites/{site_id}/geofences/{id}` - Update geofence
- `DELETE /api/admin/sites/{site_id}/geofences/{id}` - Delete geofence

### IP Rules
- `GET /api/admin/sites/{site_id}/ip-rules` - List IP rules
- `POST /api/admin/sites/{site_id}/ip-rules` - Create IP rule
- `PUT /api/admin/sites/{site_id}/ip-rules/{id}` - Update IP rule
- `DELETE /api/admin/sites/{site_id}/ip-rules/{id}` - Delete IP rule

### Audit Logs
- `GET /api/admin/sites/{site_id}/audit` - Search audit logs
- `GET /api/admin/sites/{site_id}/audit/export` - Export CSV
- `GET /api/admin/sites/{site_id}/audit/{log_id}/screenshot` - Get screenshot

### Public Site Access
- `GET /s/{site_id}/*` - Access site with filtering

## Configuration

Environment variables (see `backend/app/core/config.py`):

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT secret key
- `S3_ENDPOINT` - MinIO/S3 endpoint
- `S3_ACCESS_KEY` - MinIO/S3 access key
- `S3_SECRET_KEY` - MinIO/S3 secret key
- `S3_BUCKET` - S3 bucket name

## Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run API/e2e tests
API_BASE_URL=http://localhost:8002 npx playwright test tests/e2e/test_api.spec.ts

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=html
```

## License

MIT
