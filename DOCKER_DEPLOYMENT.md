# Docker Deployment Guide

This guide covers the containerized deployment of the Video Subtitle Scraper application using Docker and Docker Compose.

## Quick Start

### 1. Production Deployment
```bash
# Start the application
./start.sh

# Validate deployment
./validate-running.sh

# Stop the application
docker-compose down
```

### 2. Development Mode
```bash
# Start with hot reload
./dev-start.sh

# Stop development containers
docker-compose -f docker-compose.dev.yml down
```

## File Structure

```
├── docker-compose.yml          # Production configuration
├── docker-compose.dev.yml      # Development configuration with hot reload
├── start.sh                    # Production deployment script
├── dev-start.sh               # Development deployment script
├── validate-deployment.sh      # Setup validation script
├── validate-running.sh         # Runtime validation script
├── backend/
│   ├── Dockerfile             # Backend container definition
│   └── requirements.txt       # Python dependencies
└── frontend/
    ├── Dockerfile             # Frontend container definition
    └── package.json           # Node.js dependencies
```

## Services

### Backend Service
- **Port**: 8000
- **Framework**: FastAPI with Uvicorn
- **Database**: SQLite (persistent volume)
- **Health Check**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs`

### Frontend Service
- **Port**: 3000
- **Framework**: Next.js
- **Build**: Production optimized build
- **Access**: `http://localhost:3000`

## Docker Configuration

### Production (`docker-compose.yml`)
- Optimized for production deployment
- No source code mounting
- Health checks enabled
- Persistent data volumes only

### Development (`docker-compose.dev.yml`)
- Source code hot reload
- Development commands
- Volume mounts for live editing

## Networking

- Both services run on a custom bridge network (`app-network`)
- Backend accessible to frontend via service name resolution
- External access via exposed ports (3000, 8000)

## Persistent Data

The backend database is persisted using Docker volumes:
```yaml
volumes:
  - ./backend/data:/app/data
```

This ensures that:
- Database survives container restarts
- Data is preserved between deployments
- No data loss during updates

## Health Monitoring

### Backend Health Check
- Endpoint: `/health`
- Interval: 30 seconds
- Timeout: 10 seconds
- Start period: 40 seconds

### Manual Health Verification
```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend accessibility
curl -I http://localhost:3000

# View container status
docker-compose ps

# View service logs
docker-compose logs -f
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000 and 8000 are available
2. **Docker not running**: Start Docker service
3. **Build failures**: Check Docker logs and network connectivity
4. **Import errors**: Ensure proper Python path configuration

### Debugging Commands

```bash
# View container logs
docker-compose logs backend
docker-compose logs frontend

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec frontend sh

# Rebuild specific service
docker-compose build backend
docker-compose build frontend

# Force rebuild without cache
docker-compose build --no-cache

# Clean up containers and networks
docker-compose down
docker system prune
```

## Environment Variables

### Backend
- `DATABASE_URL`: SQLite database path
- `PYTHONPATH`: Python module search path

### Frontend
- `NEXT_PUBLIC_API_URL`: Backend API URL for client-side requests
- `NODE_ENV`: Node.js environment (production/development)

## Security Considerations

1. **Network isolation**: Services communicate via internal network
2. **No root users**: Containers run with minimal privileges
3. **Health checks**: Automatic service monitoring
4. **Data persistence**: Database stored in secure volumes

## Performance Optimization

1. **Multi-stage builds**: Optimized Docker images
2. **Layer caching**: Efficient build process
3. **Production builds**: Optimized frontend bundles
4. **Health monitoring**: Automatic restart on failures

## Scaling Considerations

For production scaling:
1. Use external database (PostgreSQL/MySQL)
2. Add reverse proxy (Nginx)
3. Implement horizontal scaling
4. Add monitoring and logging
5. Use container orchestration (Kubernetes)
