# MorphAPI Setup & Deployment Guide

## 1. Local Developer Setup

### Prerequisites
- **Node.js**: Version 18.18 or higher (Node.js 20+ or 24+ recommended)
- **Package Manager**: `pnpm` (v9+) or `npm` (v10+)
- **Operating System**: Linux, macOS, or Windows with WSL2
- **Optional Backend Environment**: Python 3.12 with Playwright Chromium installed

---

### Step-by-Step Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/Jayant-1/MorphAPI.git
cd MorphAPI
```

#### 2. Install Frontend Dependencies
```bash
cd Frontend
pnpm install
```

#### 3. Run Static Code Checks
Validate TypeScript types and lint rules:
```bash
pnpm run lint
pnpm run type-check
```

#### 4. Build for Production
Generate the optimized Next.js 15 production bundle:
```bash
pnpm build
```

#### 5. Start the Application Server
Run the production server on port 3000:
```bash
pnpm start
```
The application will be live at:
```text
http://localhost:3000
```

To run in development mode with hot-reloading:
```bash
pnpm dev
```

---

## 2. Environment Variables Reference

### Frontend Configuration (`Frontend/.env.local`)

| Variable | Description | Default Value | Required |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the backend FastAPI control plane | `http://localhost:8000` | No (falls back to mock fixtures) |
| `PORT` | Local port for Next.js HTTP server | `3000` | No |

### Control Plane Configuration (Backend Specification)

| Variable | Description | Default Value | Required |
|---|---|---|---|
| `NIM_API_KEY` | Authentication credential for NVIDIA NIM inference | `<placeholder>` | Yes (for live selector synthesis) |
| `NIM_BASE_URL` | Endpoint base for NVIDIA NIM service | `https://integrate.api.nvidia.com/v1` | No |
| `NIM_MODEL_ID` | Model identifier for selector reasoning | `meta/llama-3.1-70b-instruct` | No |
| `DATABASE_URL` | Connection string for SQLite or PostgreSQL | `sqlite+aiosqlite:///./morphapi.db` | No |
| `REQUIRE_APPROVAL` | Enforce human-in-the-loop approval before promoting healed selectors | `true` | No |
| `WORKER_CONCURRENCY` | Maximum concurrent Playwright browser sessions | `4` | No |
| `BROWSER_TIMEOUT_MS`| Hard deadline for page navigation and extraction | `15000` | No |

---

## 3. Production Deployment Architecture

For high-availability enterprise environments, MorphAPI separates the user-facing Next.js console from the FastAPI routing plane, browser worker pools, and relational storage.

```mermaid
flowchart TD
    subgraph IngressLayer["Edge & Ingress (Reverse Proxy / Load Balancer)"]
        Ingress["Reverse Proxy (NGINX / Caddy / Cloudflare)\nSSL Termination, DDoS Protection"]
    end

    subgraph FrontendCluster["Frontend Application Cluster"]
        FE1["Next.js Container 1\n(Standalone Node.js Server)"]
        FE2["Next.js Container 2\n(Standalone Node.js Server)"]
    end

    subgraph ApiCluster["FastAPI Control Plane Cluster"]
        API1["FastAPI ASGI Container 1\n(Uvicorn Multi-Worker)"]
        API2["FastAPI ASGI Container 2\n(Uvicorn Multi-Worker)"]
    end

    subgraph BrowserWorkerPool["Browser Worker Pool (Playwright)"]
        Worker1["Isolated Playwright Worker 1\n(Headless Chromium)"]
        Worker2["Isolated Playwright Worker 2\n(Headless Chromium)"]
    end

    subgraph StorageLayer["Persistence & Caching"]
        PG[(PostgreSQL 16 Cluster\nAuthoritative Business Registry)]
        Redis[(Redis 7 Cluster\nLangGraph Checkpoints & Job Queue)]
    end

    subgraph ExternalServices["External Providers"]
        NIM["NVIDIA NIM Inference API\n(meta/llama-3.1-70b-instruct)"]
        TargetWeb["Public Target Websites"]
    end

    Ingress -->|Route / | FrontendCluster
    Ingress -->|Route /api/v1 and /mcp | ApiCluster

    ApiCluster --> PG
    ApiCluster --> Redis
    ApiCluster -->|Dispatch Job| BrowserWorkerPool

    BrowserWorkerPool --> TargetWeb
    ApiCluster --> NIM
```

---

## 4. Production Docker Compose Specification

Below is the standard production multi-container topology (`docker-compose.yml`):

```yaml
version: "3.9"

services:
  # Next.js Frontend Console
  frontend:
    build:
      context: ./Frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=http://api:8000
    restart: unless-stopped
    depends_on:
      - api

  # FastAPI Control Plane
  api:
    build:
      context: ./Backend
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://morphapi:secure_pass@postgres:5432/morphapi_db
      - REDIS_URL=redis://redis:6379/0
      - NIM_API_KEY=${NIM_API_KEY}
      - NIM_BASE_URL=https://integrate.api.nvidia.com/v1
      - NIM_MODEL_ID=meta/llama-3.1-70b-instruct
      - REQUIRE_APPROVAL=true
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Dedicated Playwright Browser Worker Pool
  browser-worker:
    build:
      context: ./Backend
      dockerfile: Dockerfile.worker
    environment:
      - REDIS_URL=redis://redis:6379/0
      - WORKER_CONCURRENCY=4
      - BROWSER_TIMEOUT_MS=15000
    restart: unless-stopped
    depends_on:
      - redis

  # PostgreSQL Authoritative Business Database
  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=morphapi_db
      - POSTGRES_USER=morphapi
      - POSTGRES_PASSWORD=secure_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U morphapi -d morphapi_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis Checkpoint & Task Queue
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

---

## 5. Production Scaling & Worker Isolation Recommendations

1. **Decouple Browser Workloads from the Control Plane**:
   - Playwright Chromium instances consume significant RAM (~150MB per active tab) and burst CPU during rendering.
   - Never run browser extraction inside the primary FastAPI ASGI server process. Use worker queues (Celery, ARQ, or Redis Streams) to dispatch browser jobs to dedicated worker nodes.
2. **Stateless API Scaling**:
   - The FastAPI control plane is completely stateless; it can scale horizontally behind a round-robin load balancer.
3. **Database Connection Pooling**:
   - When deploying multiple API replicas, use PgBouncer or SQLAlchemy connection pooling to prevent exhausting PostgreSQL connection limits.
4. **Health Check Probes**:
   - **Liveness Probe**: `GET /api/v1/health/live` (confirms process responsiveness).
   - **Readiness Probe**: `GET /api/v1/health/ready` (confirms connectivity to PostgreSQL, Redis, and NVIDIA NIM tool-calling compatibility).
