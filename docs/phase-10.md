# Phase 10: AI Financial Assistant

## Implemented

- ChatGPT-style AI assistant UI
- Persistent chat sessions
- Persistent user and assistant messages
- OpenAI Responses API integration
- Context building from:
  - Stock data
  - News data
  - News sentiment
- Protected backend chat APIs
- Sidebar navigation entry for AI Assistant
- Backend route test coverage with mocked service calls

## Database

### `chat_sessions`

- `id`
- `user_id`
- `title`
- `created_at`
- `updated_at`

### `chat_messages`

- `id`
- `session_id`
- `role`
- `content`
- `created_at`

Each chat session belongs to an authenticated user.

## Backend API

- `GET /api/v1/chat/sessions`
- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions/{session_id}`
- `POST /api/v1/chat/sessions/{session_id}/messages`

All endpoints require authentication.

## OpenAI Configuration

Set these values in `.env` or `backend/.env`:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

The backend calls the OpenAI Responses API through `httpx`, using the existing backend dependency stack.

If `OPENAI_API_KEY` is missing, the assistant stores the user message and returns a setup guidance response instead of crashing.

## Frontend

- `/assistant`

The UI includes:

- Saved chat history
- New chat button
- Suggested prompts
- Chat transcript
- Message composer

## Guardrails

The assistant prompt requires informational research support only. It should not provide personalized financial advice, buy/sell instructions, guarantees, or price targets.

## Testing

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
```

## Manual Test

1. Start the stack:

```bash
docker compose up --build
```

2. Login and open:

```text
http://localhost:3000/assistant
```

3. Ask:

```text
Why did Tesla move today?
```

4. Confirm the assistant creates a saved chat session and returns an informational answer.
