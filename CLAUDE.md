# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Sulthan AI Lab Personal Assistant** - A full-stack AI-powered productivity assistant application that integrates with Google Workspace (Gmail, Calendar, Chat, Docs) to help manage tasks, reminders, and provide productivity suggestions.

## Tech Stack

- **Backend**: FastAPI (Python 3.13+) with PostgreSQL
- **Frontend**: Next.js 15 + React 19 + TailwindCSS
- **LLM**: LiteLLM gateway proxy (localhost:4000)
- **Database**: PostgreSQL
- **Auth**: NextAuth.js with Google OAuth

## Development Commands

### Backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate  # Windows
pip install -r requirements.txt
fastapi dev app/main.py                          # Dev server (port 8000)
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # Dev server (port 3000)
npm run build  # Production build
```

### Full Stack

```bash
# 1. Ensure PostgreSQL is running and reachable
# 2. Ensure LLM Gateway is running (localhost:4000)

# 3. Start Backend
cd backend && fastapi dev app/main.py

# 4. Start Frontend (new terminal)
cd frontend && npm run dev
```

## Architecture

### Data Flow
```
Frontend (Next.js) → Backend (FastAPI) → LLM Gateway (LiteLLM) → LLM Providers
       ↓                    ↓
   NextAuth.js         PostgreSQL
   (Google OAuth)      Google APIs (Gmail, Calendar, Chat, Docs)
```

### Key Features
1. **Data Sync**: Gmail, Calendar, Chat, Docs sync every 15 min
2. **Task Management**: CRUD with statuses (done, in_progress, on_hold, assigned)
3. **AI Task Extraction**: LLM extracts tasks from emails/docs
4. **Reminders**: Email + Calendar + In-app notifications
5. **AI Suggestions**: Productivity tips based on patterns
6. **WebSocket**: Real-time sync progress and notifications

## Project Structure

```
sulthan-ai-lab-personal-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── api/              # Route handlers
│   │   ├── core/             # Business logic, config
│   │   ├── crud/             # Database operations
│   │   ├── schemas/          # Pydantic models
│   │   └── middleware/       # Request middleware
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages
│   │   ├── components/       # React components
│   │   └── lib/              # API clients, utilities
│   └── package.json
└── CLAUDE.md
```

## Environment Variables

### Backend (.env)
```
POSTGRES_DSN=postgresql://user:password@localhost:5432/assistant_db
LLM_GATEWAY_URL=http://localhost:4000
LLM_GATEWAY_KEY=your-llm-gateway-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
NEXTAUTH_SECRET=your-nextauth-secret
```

### Frontend (.env)
```
NEXT_PUBLIC_BACKEND_URL_API=http://localhost:8000
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000/ws
GOOGLE_CLIENT_ID=<same as backend>
GOOGLE_CLIENT_SECRET=<same as backend>
NEXTAUTH_SECRET=<same as backend>
```

## API Patterns

### Headers
- `Authorization: Bearer <jwt_token>` - User authentication
- WebSocket: `/ws/{user_id}` - Real-time updates

### Task Status Flow
```
assigned → in_progress → done
              ↓
          on_hold
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/core/config.py` | Pydantic Settings configuration |
| `backend/app/crud/db_connection.py` | PostgreSQL connection manager |
| `backend/app/core/google_api_client.py` | Google API wrapper |
| `backend/app/core/task_extractor.py` | AI task extraction |
| `frontend/src/app/auth.ts` | NextAuth configuration |
| `frontend/src/lib/axios-instance.ts` | API client with auth |
