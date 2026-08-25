# Rai Backend API

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Django Version](https://img.shields.io/badge/django-5.2.8-green)
![Django REST Framework](https://img.shields.io/badge/drf-3.16-red)
![Celery](https://img.shields.io/badge/celery-5.4-brightgreen)
![Redis](https://img.shields.io/badge/redis-7.0-red)
![Docker](https://img.shields.io/badge/docker-ready-blue)

A high-performance, production-ready Django API backend designed for the Rai application. This backend leverages modern architectural patterns, advanced caching, message brokering, and asynchronous task execution to deliver a highly scalable infrastructure capable of serving real-time messaging, AI interactions, community platforms, and sports betting analytics.

---

## 🚀 Unique Features & Core Capabilities

- **Multi-Factor Authentication & Identity Management**: 
  - Supports Email, Phone, and Google OAuth logins.
  - OTP-based identity verification via Anymail & Infobip integrations.
  - Granular account locking and failed-login attack prevention.
- **Real-Time AI & Token Tracking**: 
  - Asynchronous generation of AI responses processed by heavy-duty Celery queues.
  - WebSocket streams (via Django Channels) for low-latency AI conversations.
  - Deep multimedia support: audio transcription and image context awareness.
- **Community & Social Platform**:
  - Secure real-time WebSocket chat rooms.
  - Private and Public communities with join request workflows.
  - Rotateable invite codes and strict role-based access control (RBAC).
- **Advanced Sports Betting Integration**:
  - Live synchronization of odds via "The Odds API" (Celery Beat).
  - In-depth analytic models including Edge Percentage, Expected Value (EV), and Confidence scores.
  - Custom User Parlays with automated risk-level evaluation.
- **Enterprise-Grade Infrastructure & Performance**:
  - PgBouncer connection pooling for optimized PostgreSQL loads.
  - Sub-millisecond data caching with Redis and `django-redis` (Signals-based cache invalidation).
  - Rapid JSON Serialization using `ujson`.
  - Configurable application-wide rate limiting and custom `LatencyMiddleware`.

---

## 📊 Project Metrics & Size

Based on a comprehensive structural analysis, the repository scales efficiently with the following metrics:
- **~489 Core Source Files** (excluding environments and standard assets)
- **6 Extensible Django Applications** (`authentication`, `ai`, `community`, `support`, `dashboard`, `betting`)
- **15 Primary Database Models** driving business logic
- **7 Docker Services** mapped in `docker-compose.yml` (`nginx`, `web`, `db-migrator`, `celery_ai`, `celery_heavy`, `celery_beat`, `redis`, `pgbouncer`)

---

## 📁 Project Architecture (Apps)

The system is decomposed into highly cohesive, decoupled applications:

1. **`authentication`**: Core user management, custom User model, OTP workflows, SimpleJWT implementations, and third-party OAuth.
2. **`ai`**: Handles user-AI conversations, token accounting (via `tiktoken`), and task orchestration for large language model generation.
3. **`community`**: Manages micro-communities, membership roles, and WebSocket-driven chat rooms.
4. **`betting`**: Aggregates match data, expert picks, user parlays, and odds syncing logic.
5. **`support`**: A fully functional ticketing system for user-admin communications.
6. **`dashboard`**: Admin-focused module for managing dynamic app pages (Privacy Policies, Terms) and overarching entities.

---

## 🛠 Tech Stack

### Core
- **Framework**: Django 5.2.8 + Django REST Framework 3.16.0
- **Asynchronous Protocol**: Django Channels + Daphne/Uvicorn
- **Language**: Python 3.10+
- **Serialization**: `ujson`

### Data & Caching
- **Primary Database**: PostgreSQL (configured dynamically via `dj-database-url`)
- **Connection Pooler**: PgBouncer
- **Cache & Message Broker**: Redis 7

### Task Queue & Background Jobs
- **Workers**: Celery 5.4.0 (Prefork and Thread pools depending on task density)
- **Scheduler**: Celery Beat

### Deployment & DevOps
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx (Reverse Proxy) + Gunicorn
- **Storage**: AWS S3 (via `django-storages` and `boto3`)

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Docker & Docker Compose (for containerized deployment)
- Redis Server (if running natively)
- PostgreSQL (if running natively)

### Environment Variables
Copy `.env.example` to `.env` and fill in the required values:
```bash
cp .env.example .env
```
_Ensure you add your `SECRET_KEY`, `THE_ODDS_API_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`, and Infobip/AWS credentials._

### Running via Docker (Recommended)
The easiest way to boot the entire stack (Web, Nginx, Redis, PgBouncer, Celery, Migrator) is via Docker Compose:

```bash
# Build and spin up the containers in detached mode
docker-compose up --build -d

# Check the logs of the web instances
docker-compose logs -f web
```
*Note: The `db-migrator` service will automatically apply all Django migrations upon startup.*

### Running Locally (Native)
1. **Create Virtual Environment & Install Dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Apply Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
3. **Run the Development Server**:
   ```bash
   python manage.py runserver
   ```
4. **Start Celery (In separate terminal windows)**:
   ```bash
   celery -A Rai_Backend worker -l info
   celery -A Rai_Backend beat -l info
   ```

---

## 🔌 API Overview

The API is fully documented via Swagger/OpenAPI. Once running, access the documentation at:
- **Swagger UI**: `/api/docs/`
- **OpenAPI Schema**: `/api/schema/`

### Key Endpoint Prefixes:
- `POST /api/auth/` - Authentication, OTPs, Token generation.
- `GET/POST /api/ai/` - Conversations, message generation, transcriptions.
- `GET/POST /api/community/` - Community management and invites.
- `GET/POST /api/betting/` - Real-time matches, expert picks, and parlay construction.
- `GET/POST /api/support/` - Ticket creation and updates.

---

## 🔒 Security & Optimization Notes

- **Throttling**: The API utilizes DRF's `ScopedRateThrottle` for anonymous requests, OTP requests, logins, media uploads, and community interactions to prevent abuse.
- **Cache Invalidation**: Signals are explicitly written in model `.save()` and `.delete()` methods to clear specific Redis keys instantly, ensuring state consistency without relying entirely on TTLs.
- **Routing Isolation**: Celery limits AI Generation tasks to a dedicated `heavy_queue` running on `prefork` pools to prevent blocking fast IO tasks running on the `default` threaded pool.

---
*Built with precision and high standards for scalability.*
"# rai-backend-" 
"# rai-backend-" 
