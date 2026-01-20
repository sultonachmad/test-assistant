# Sulthan AI Lab - Personal Assistant

AI-powered productivity assistant that integrates with Google Workspace (Gmail, Calendar, Docs) to help manage tasks, reminders, and provide productivity suggestions.

## Features

- **Task Management**: Create, update, and track tasks with statuses (Done, In Progress, On Hold, Assigned)
- **Reminders**: Set reminders with multiple delivery channels (Email, Calendar, In-App)
- **Google Integration**: Sync with Gmail, Calendar, and Google Docs
- **AI Suggestions**: Get productivity tips based on your tasks and patterns
- **Real-time Updates**: WebSocket support for instant notifications

## Tech Stack

- **Backend**: FastAPI (Python 3.13+)
- **Frontend**: Next.js 15 + React 19 + TailwindCSS
- **Database**: PostgreSQL
- **LLM**: LiteLLM Gateway (localhost:4000)
- **Auth**: NextAuth.js with Google OAuth

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 22+
- PostgreSQL (running on 192.168.9.227:5439)
- LLM Gateway running on localhost:4000

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run development server
fastapi dev app/main.py
```

Backend will be available at http://localhost:8000

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at http://localhost:3000

## Environment Variables

### Backend (.env)

```env
POSTGRES_DSN=postgresql://postgres:password$1@192.168.9.227:5439/sultan_assistant
LLM_GATEWAY_URL=http://localhost:4000
LLM_GATEWAY_KEY=test123
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
NEXTAUTH_SECRET=your-secret
```

### Frontend (.env)

```env
NEXT_PUBLIC_BACKEND_URL_API=http://localhost:8000
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000/ws
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
NEXTAUTH_SECRET=your-secret
```

## Password Encryption

Sensitive values in the backend `.env` file can be encrypted for additional security. The encryption uses Fernet symmetric encryption with `NEXTAUTH_SECRET` as the key.

### Supported Encrypted Fields

- `GOOGLE_CLIENT_SECRET`
- `SMTP_PASSWORD`
- `TAIGA_PASSWORD`
- `TAIGA_AUTH_TOKEN`
- `LLM_GATEWAY_KEY`

### How to Encrypt a Password

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Run the encryption utility:
   ```bash
   python -m app.core.encryption
   ```

3. Enter your `NEXTAUTH_SECRET` when prompted (or set it as environment variable)

4. Enter the password you want to encrypt

5. Copy the output (starts with `ENC:`) to your `.env` file

### Example

```env
# NEXTAUTH_SECRET must be plaintext (used as encryption key)
NEXTAUTH_SECRET=your-secret-key-here

# Encrypted values (auto-decrypted on startup)
TAIGA_PASSWORD=ENC:gAAAAABnR5Kv...
SMTP_PASSWORD=ENC:gAAAAABnR5Lw...
GOOGLE_CLIENT_SECRET=ENC:gAAAAABnR5Mx...

# Plaintext values still work
LLM_GATEWAY_KEY=test123
```

The backend automatically detects and decrypts any value prefixed with `ENC:` when loading settings.

## Google Cloud Console Setup

To enable Google Workspace sync (Gmail, Calendar, Docs), you must enable the following APIs in your Google Cloud Console:

### Required APIs

1. **Google Calendar API**
   - URL: https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview
   - Required for: Calendar event sync and creation

2. **Gmail API**
   - URL: https://console.developers.google.com/apis/api/gmail.googleapis.com/overview
   - Required for: Email sync and reading

3. **Google Drive API**
   - URL: https://console.developers.google.com/apis/api/drive.googleapis.com/overview
   - Required for: Listing and browsing Google Docs

4. **Google Docs API**
   - URL: https://console.developers.google.com/apis/api/docs.googleapis.com/overview
   - Required for: Reading document content

5. **Google Sheets API**
   - URL: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview
   - Required for: Syncing tasks from Google Sheets

### How to Enable

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (same project as your OAuth credentials)
3. Navigate to **APIs & Services** > **Library**
4. Search for each API listed above and click **Enable**
5. Wait 1-2 minutes for changes to propagate

### OAuth Consent Screen

Ensure your OAuth consent screen includes these scopes:
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/calendar.events`
- `https://www.googleapis.com/auth/drive.readonly`
- `https://www.googleapis.com/auth/documents.readonly`
- `https://www.googleapis.com/auth/spreadsheets.readonly`

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
sulthan-ai-lab-personal-assistant/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Business logic
│   │   ├── crud/         # Database operations
│   │   ├── schemas/      # Pydantic models
│   │   └── main.py       # Entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js pages
│   │   ├── components/   # React components
│   │   └── lib/          # API clients
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Task Statuses

- **Assigned**: New task, not yet started
- **In Progress**: Currently being worked on
- **On Hold**: Temporarily paused
- **Done**: Completed

## License

Private - BDO AI Lab

# TODO

  - Google API sync implementation (Gmail, Calendar, Docs actual sync)
  - AI task extraction from emails
  - Reminder scheduler background worker
  - Email sending via SMTP
  - Taiga integration (placeholder ready)