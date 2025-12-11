# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Full Stack Development
```bash
# Start both frontend and backend simultaneously
npm run dev

# Or start individually:
# Backend (from project root or backend/)
cd backend && source venv/bin/activate && python start.py
# Alternative: uvicorn main:app --reload

# Frontend (from frontend/)
cd frontend && npm start
```

### Backend Commands
```bash
# Setup virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_api_endpoints.py
python test_claude_v2.py
python test_voice_actor_api.py
```

### Frontend Commands
```bash
cd frontend
npm install           # Install dependencies
npm start            # Start dev server (port 3000)
npm run build        # Build for production
npm test             # Run tests (if configured)
```

## Architecture Overview

### Request Flow Pipeline
The application follows a multi-stage video ad creation workflow:

1. **Frontend Entry** (`frontend/src/App.tsx`) → Routes to video-ads-v2 components
2. **API Gateway** (`backend/video_ads_v2_routes.py`) → FastAPI endpoints with JWT auth
3. **Workflow Orchestration** (`backend/workflow_v2_manager.py`) → Manages 4-phase analysis
4. **AI Integration** (`backend/claude_v2_client.py`) → Claude API with 9-minute timeout

### Core Workflow Phases
The marketing analysis pipeline processes through sequential phases, each building on previous results:
- **Phase 1**: Avatar Analysis (target audience profiling)
- **Phase 2**: Journey Mapping (customer pain points)
- **Phase 3**: Objections Analysis (purchase barriers)
- **Phase 4**: Angles Generation (marketing strategies)

### Authentication Architecture
- **Token Flow**: Supabase JWT → Backend verification → User context
- **Fallback**: Dev-token support when JWT expires (`frontend/src/pages/video-ads-v2/ImportFromURL.tsx:54-69`)
- **Protected Routes**: All /video-ads-v2/* routes require authentication

### AI Service Integration
- **OpenAI GPT-4o-mini**: URL parsing and product extraction (8000 char limit)
- **Claude (Anthropic)**: Creative content generation with YAML prompt templates
- **ElevenLabs**: Voice synthesis (integrated but optional)
- **Hedra**: Video generation (integrated but optional)

### State Management
- **Frontend**: Component state + localStorage for workflow persistence
- **Backend**: Conversation tracking via `active_conversations` dict (ready for Redis migration)
- **Workflow State**: Maintained across phases with UUID-based conversation IDs

## Key Files and Their Roles

### Backend Core Files
- `main.py`: FastAPI server initialization, CORS, static file serving
- `video_ads_v2_routes.py:87-197`: Main route handlers for V2 workflow
- `workflow_v2_manager.py:14-137`: Orchestrates multi-phase Claude analysis
- `claude_v2_client.py`: Claude API client with prompt management
- `auth.py`: Supabase JWT verification and user context

### Frontend Core Files
- `App.tsx`: Route definitions and auth provider wrapper
- `contexts/AuthContext.tsx`: Supabase auth state management
- `pages/video-ads-v2/*`: V2 workflow UI components
- `pages/facebook-integration/*`: Facebook OAuth and analytics

### Configuration Files
- `backend/prompts_v2/*.yaml`: Claude prompt templates for each phase
- `backend/.env`: API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, SUPABASE_*)
- `frontend/.env`: React app config (REACT_APP_SUPABASE_*, REACT_APP_API_URL)

## Environment Variables

### Required Backend Variables
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_JWT_SECRET=your_jwt_secret
ANTHROPIC_API_KEY=your_claude_key  # For V2 workflow
OPENAI_API_KEY=your_openai_key     # For URL parsing
```

### Optional Backend Variables
```bash
ELEVENLABS_API_KEY=your_elevenlabs_key  # Voice generation
HEDRA_API_KEY=your_hedra_key            # Video creation
FACEBOOK_APP_ID=your_fb_app_id          # Facebook integration
FACEBOOK_APP_SECRET=your_fb_secret
```

### Frontend Variables
```bash
REACT_APP_SUPABASE_URL=your_supabase_url
REACT_APP_SUPABASE_ANON_KEY=your_anon_key
REACT_APP_API_URL=http://localhost:8000  # Backend URL
```

## Database Schema
The app uses Supabase (PostgreSQL) with migrations in `backend/migrations/`:
- User authentication (handled by Supabase Auth)
- Facebook integration tables (`add_facebook_tables.sql`)
- ElevenLabs voices cache (`create_elevenlabs_voices_table.sql`)

## Testing Approach
- **Backend**: Individual test files for each service (`test_*.py`)
- **Frontend**: Component testing with React Testing Library
- **Integration**: `test_complete_flow.py` for end-to-end workflow

## Deployment Notes
- **Frontend**: Configured for Vercel deployment (see `vercel.json`)
- **Backend**: Deployed on AWS Lightsail using Docker
  - Uses docker-compose for container management
  - Service runs as `sucana-backend` container
  - Deployment steps:
    1. SSH into Lightsail instance
    2. `cd /home/ubuntu/sucana-v4`
    3. `git pull origin main`
    4. `cd backend`
    5. `docker-compose build`
    6. `docker-compose down && docker-compose up -d`
    7. Check logs: `docker-compose logs --tail=50`
- **SSL**: Local HTTPS setup available (`ssl/` directory, `setup_ssl.sh`)

## Common Development Patterns

### Adding New Workflow Phases
1. Create prompt template in `backend/prompts_v2/`
2. Add phase method in `workflow_v2_manager.py`
3. Update models in `video_ads_v2_models.py`
4. Create frontend component in `pages/video-ads-v2/`

### API Endpoint Pattern
```python
@router.post("/endpoint", response_model=ResponseModel)
async def endpoint_name(
    request: RequestModel,
    current_user: dict = Depends(verify_token)
):
    user_id = current_user["user_id"]
    # Implementation
```

### Frontend API Call Pattern
```typescript
const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v2/endpoint`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
});
```

## Current Development Focus
- Migration from OpenAI to Claude for content generation (V2 workflow)
- Facebook integration enhancement
- Audio/video generation pipeline improvements
- Workflow state persistence and recovery
- now added Supabase-schema.csv file in the project root folder. add it to memory.