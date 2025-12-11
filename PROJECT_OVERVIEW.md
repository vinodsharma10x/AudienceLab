# AudienceLab - Marketing Research & Content Generation Platform

## Overview

**AudienceLab** is a full-stack marketing research platform that uses AI to understand your audience and generate resonant marketing content. It takes a product URL or manual product information and creates compelling hooks, scripts, and marketing angles through an intelligent multi-phase workflow powered by Claude AI.

The platform also integrates with Facebook's Marketing API to enable campaign creation, publishing, and performance analytics.

---

## Core Value Proposition

1. **Automated Marketing Research** - AI analyzes your product and target audience
2. **Content Generation** - Creates hooks, scripts, and marketing angles
3. **Video Production** - Generates audio (ElevenLabs) and video (Hedra)
4. **Campaign Management** - Publishes to Facebook and tracks performance

---

## Tech Stack

### Frontend
- **React 19** with TypeScript
- **Material-UI (MUI)** v7 for components
- **React Router** v7 for navigation
- **Supabase** for authentication
- Deployed on **Vercel**

### Backend
- **FastAPI** (Python) with async/await
- **Supabase** (PostgreSQL) for database
- **Claude AI** (Anthropic) for content generation
- **OpenAI GPT-4o-mini** for URL parsing
- **ElevenLabs** for voice synthesis
- **Hedra** for video generation
- **AWS S3** for media storage
- Deployed on **AWS Lightsail** (Docker)

---

## Architecture

### Request Flow
```
Frontend (React)
    → API Gateway (FastAPI)
    → Workflow Manager
    → Claude AI Pipeline
    → Database (Supabase)
    → Media Services (ElevenLabs, Hedra)
    → Storage (S3)
```

### Authentication
- JWT tokens issued by Supabase Auth
- Backend verifies tokens against Supabase JWT secret
- Protected routes require valid Bearer token
- Development fallback token supported for testing

---

## Core Workflow: Video Ad Creation

### Phase 1: Product Import
**File:** `backend/video_ads_v3_routes.py`, `frontend/src/pages/video-ads-v2/ImportFromURL.tsx`

- User provides a product URL or enters information manually
- OpenAI GPT-4o-mini parses the URL and extracts product data
- Creates a new campaign in the database

### Phase 2: Product Information Review
**File:** `frontend/src/pages/video-ads-v2/ProductInfo.tsx`

- User reviews and edits extracted product information:
  - Product name
  - Description
  - Target audience
  - Price
  - Problem solved
  - Differentiation

### Phase 3: Marketing Analysis (4-Phase Claude Pipeline)
**File:** `backend/workflow_v2_manager.py`

The core AI workflow runs 4 sequential phases, each building on the previous:

| Phase | Purpose | Output |
|-------|---------|--------|
| **Avatar Analysis** | Builds ideal customer profile | Demographics, psychographics, pain points |
| **Journey Mapping** | Maps customer decision process | Discovery → Consideration → Decision phases |
| **Objections Analysis** | Identifies purchase barriers | Solution objections, internal objections |
| **Angles Generation** | Creates marketing strategies | 7 positive + 7 negative angles |

Each phase uses YAML prompt templates from `backend/prompts_v2/`:
- `avatar_analysis.yaml`
- `journey_mapping.yaml`
- `objections_analysis.yaml`
- `angles_generation.yaml`

### Phase 4: Marketing Angles Selection
**File:** `frontend/src/pages/video-ads-v2/MarketingAngles.tsx`

- User reviews generated angles (14 total)
- Selects which angles to develop further
- Each angle represents a different marketing approach

### Phase 5: Hooks Generation
**File:** `frontend/src/pages/video-ads-v2/HooksV2.tsx`

- Claude generates attention-grabbing hooks for selected angles
- Hooks are categorized by type (question, story, statistic, etc.)
- User selects hooks to use for scripts

### Phase 6: Script Generation
**File:** `frontend/src/pages/video-ads-v2/Scripts.tsx`

- Claude creates full AIDA scripts for selected hooks
- Scripts are 130-170 words each
- Multiple variations per hook
- User selects final scripts

### Phase 7: Voice Actor Selection
**File:** `frontend/src/pages/video-ads-v2/VoiceActor.tsx`

- Displays available ElevenLabs voices
- User previews and selects voice
- Also selects visual actor for video

### Phase 8: Audio Generation
**File:** `frontend/src/pages/video-ads-v2/Audio.tsx`

- ElevenLabs synthesizes voice for each script
- Audio files stored in S3
- User can preview and approve

### Phase 9: Video Generation
**File:** `frontend/src/pages/video-ads-v2/Video.tsx`

- Hedra generates video with selected actor
- Lip-syncs to generated audio
- Final video stored in S3

---

## Facebook Integration

### OAuth Connection
**File:** `backend/facebook_routes.py`, `frontend/src/pages/facebook-integration/FacebookConnectPage.tsx`

- User connects Facebook account via OAuth 2.0
- App requests permissions for ads management
- Stores long-lived access token in database

### Ad Account Selection
- User selects which ad accounts to use
- Supports multiple ad accounts per Facebook account

### Campaign Creation
**File:** `backend/facebook_campaign_routes.py`, `frontend/src/pages/facebook-integration/CampaignCreateConfigure.tsx`

- Create Facebook campaigns from generated content
- Configure targeting, budget, scheduling
- Publish directly to Facebook Ads Manager

### Analytics & Reporting
**File:** `frontend/src/pages/facebook-integration/FacebookAnalytics.tsx`, `FacebookConversionReportV2.tsx`

- Syncs performance data from Facebook
- Displays metrics: spend, impressions, clicks, CTR, CPC
- Conversion tracking and ROI analysis

---

## Database Schema (Supabase)

### Core Tables

| Table | Purpose |
|-------|---------|
| `video_ads_v2_campaigns` | Campaign records with user/conversation linking |
| `video_ads_v2_product_info` | Product data for each campaign |
| `video_ads_v2_marketing_analysis` | AI-generated analysis results |
| `video_ads_v2_hooks` | Generated hooks data |
| `video_ads_v2_scripts` | Generated scripts data |
| `video_ads_v2_selections` | User voice/actor selections |
| `video_ads_v2_media` | Generated audio/video files |

### Facebook Tables

| Table | Purpose |
|-------|---------|
| `facebook_accounts` | Connected Facebook accounts |
| `facebook_ad_accounts` | Linked ad accounts |
| `facebook_ad_performance` | Synced performance metrics |
| `facebook_performance_summary` | Aggregated analytics view |

### System Tables

| Table | Purpose |
|-------|---------|
| `sessions` | Workflow session tracking |
| `steps` | Individual step progress |
| `assistant_calls` | AI API call logging (cost tracking) |
| `elevenlabs_voices` | Cached voice options |

---

## API Endpoints

### Video Ads V2/V3 (`/video-ads-v2/*`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/start` | Start new campaign |
| POST | `/parse-url` | Extract product info from URL |
| POST | `/product-info` | Save product information |
| POST | `/analyze` | Run 4-phase marketing analysis |
| POST | `/generate-hooks` | Generate hooks for angles |
| POST | `/generate-scripts` | Generate scripts for hooks |
| POST | `/generate-audio` | Create audio with ElevenLabs |
| POST | `/generate-video` | Create video with Hedra |
| GET | `/campaigns` | List user's campaigns |
| GET | `/campaign/{id}` | Get campaign details |

### Facebook (`/facebook/*`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/auth-url` | Get OAuth authorization URL |
| GET | `/callback` | Handle OAuth callback |
| GET | `/accounts` | List connected accounts |
| GET | `/ad-accounts` | List ad accounts |
| POST | `/sync` | Sync performance data |
| GET | `/analytics` | Get analytics data |

### Facebook Campaigns (`/facebook-campaigns/*`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/create` | Create new Facebook campaign |
| POST | `/publish` | Publish campaign to Facebook |
| GET | `/{id}` | Get campaign details |

---

## Project Structure

```
audiencelab/
├── backend/
│   ├── main.py                          # FastAPI app initialization
│   ├── auth.py                          # JWT authentication
│   ├── video_ads_v3_routes.py           # Main video ads API (99KB)
│   ├── workflow_v2_manager.py           # Claude orchestration
│   ├── claude_v2_client.py              # Claude API client
│   ├── facebook_routes.py               # Facebook OAuth & API (60KB)
│   ├── facebook_campaign_routes.py      # Campaign creation
│   ├── facebook_api_service.py          # Facebook Graph API
│   ├── s3_service.py                    # AWS S3 operations
│   ├── hedra_client.py                  # Video generation
│   ├── prompts_v2/                      # YAML prompt templates
│   │   ├── avatar_analysis.yaml
│   │   ├── journey_mapping.yaml
│   │   ├── objections_analysis.yaml
│   │   ├── angles_generation.yaml
│   │   ├── hooks_generation.yaml
│   │   └── scripts_generation.yaml
│   ├── migrations/                      # SQL migrations
│   └── requirements.txt                 # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                      # Routes & theme
│   │   ├── contexts/AuthContext.tsx     # Auth state
│   │   ├── components/
│   │   │   ├── DashboardLayout.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── Sidebar.tsx
│   │   └── pages/
│   │       ├── video-ads-v2/            # Main workflow UI
│   │       │   ├── ImportFromURL.tsx
│   │       │   ├── ProductInfo.tsx
│   │       │   ├── MarketingAngles.tsx
│   │       │   ├── HooksV2.tsx
│   │       │   ├── Scripts.tsx
│   │       │   ├── VoiceActor.tsx
│   │       │   ├── Audio.tsx
│   │       │   └── Video.tsx
│   │       └── facebook-integration/    # Facebook UI
│   │           ├── FacebookDashboard.tsx
│   │           ├── FacebookConnectPage.tsx
│   │           └── FacebookAnalytics.tsx
│   └── package.json
│
├── docker-compose.yml                   # Container orchestration
├── Dockerfile                           # Backend container
├── vercel.json                          # Frontend deployment
├── CLAUDE.md                            # Development guide
└── Supabase-schema.csv                  # Database schema
```

---

## Version Evolution

The codebase contains multiple parallel implementations showing evolution:

| Version | Description | Status |
|---------|-------------|--------|
| **V1** | Original OpenAI-only workflow | Legacy |
| **V2** | Claude-powered with in-memory state | Replaced |
| **V3** | Stateless with full DB persistence | **Active** |
| **V4** | Experimental content library approach | In Development |

The main routes in `main.py:249-250` show V3 is currently active:
```python
from video_ads_v3_routes import router as video_ads_v3_router
app.include_router(video_ads_v3_router)
```

---

## Environment Variables

### Backend Required
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_JWT_SECRET=your_jwt_secret
ANTHROPIC_API_KEY=your_claude_key
OPENAI_API_KEY=your_openai_key
```

### Backend Optional
```bash
ELEVENLABS_API_KEY=your_elevenlabs_key
HEDRA_API_KEY=your_hedra_key
FACEBOOK_APP_ID=your_fb_app_id
FACEBOOK_APP_SECRET=your_fb_secret
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
S3_BUCKET_NAME=your_bucket
```

### Frontend
```bash
REACT_APP_SUPABASE_URL=your_supabase_url
REACT_APP_SUPABASE_ANON_KEY=your_anon_key
REACT_APP_API_URL=http://localhost:8000
```

---

## Development Commands

### Start Full Stack
```bash
npm run dev  # Runs both frontend and backend
```

### Backend Only
```bash
cd backend
source venv/bin/activate
python start.py  # or: uvicorn main:app --reload
```

### Frontend Only
```bash
cd frontend
npm start
```

### Deploy Backend (Lightsail)
```bash
ssh lightsail-instance
cd /home/ubuntu/audiencelab
git pull origin main
cd backend
docker-compose build
docker-compose down && docker-compose up -d
```

---

## Key Design Decisions

1. **Claude over OpenAI for content**: Claude's longer context window and creative writing quality suited the marketing content generation better.

2. **YAML prompt templates**: Prompts are externalized to YAML files for easy iteration without code changes.

3. **Stateless V3 architecture**: Moved from in-memory conversation tracking to full database persistence for reliability.

4. **Multi-phase analysis**: Breaking the marketing research into 4 distinct phases ensures comprehensive analysis that builds context.

5. **S3 for media storage**: Generated audio/video files stored in S3 rather than local filesystem for scalability.

6. **Supabase for everything**: Single platform handles auth, database, and real-time needs.

---

## Common Patterns

### Backend API Endpoint
```python
@router.post("/endpoint", response_model=ResponseModel)
async def endpoint_name(
    request: RequestModel,
    current_user: dict = Depends(verify_token)
):
    user_id = current_user["user_id"]
    # Implementation
```

### Frontend API Call
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

---

## Summary

AudienceLab is a sophisticated marketing research platform that:
- Uses AI (Claude) to research products and generate marketing content
- Produces complete video advertisements with voice and video synthesis
- Integrates with Facebook for campaign management and analytics
- Built with modern React/FastAPI architecture on cloud infrastructure

The platform automates what would traditionally take a marketing team days or weeks - from product research to published video ad campaigns.
