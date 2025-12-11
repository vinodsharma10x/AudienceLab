# AudienceLab - Claude Code Context Memory

## Project Rename Summary (Dec 11, 2025)

The project was renamed from **Sucana v4** to **AudienceLab**.

### What AudienceLab Does
- Marketing research and content generation platform
- Uses AI (Claude) to research products and understand target audiences
- Generates resonant marketing content: angles, hooks, scripts
- Multi-phase workflow:
  1. **Avatar Analysis** - target audience profiling
  2. **Journey Mapping** - customer decision process
  3. **Objections Analysis** - purchase barriers
  4. **Angles Generation** - marketing strategies (7 positive + 7 negative)
  5. **Hooks Generation** - attention-grabbing openers
  6. **Scripts Generation** - full AIDA scripts
- Optional: Audio (ElevenLabs) and Video (Hedra) generation
- Facebook integration for campaign management (routes exist but UI removed)

### Tech Stack
- **Frontend**: React 19, TypeScript, Material-UI v7, Supabase Auth
- **Backend**: FastAPI (Python), Claude AI, OpenAI (URL parsing), Supabase (PostgreSQL)
- **Deployment**: Frontend on Vercel, Backend on AWS Lightsail (Docker)

---

## Files Updated for Rename (Sucana → AudienceLab)

### Frontend UI Files
- `src/components/Sidebar.tsx` - Logo "AudienceLab", avatar letter "A"
- `src/pages/LoginPage.tsx` - Marketing tagline
- `src/pages/SignUpPage.tsx` - Join message, account text
- `src/pages/HelpPage.tsx` - Intro, support@audiencelab.io, docs.audiencelab.io
- `src/pages/DashboardPage.tsx` - Onboarding message

### Legal Pages
- `src/pages/legal/TermsOfService.tsx` - Service name, description, support@audiencelab.io
- `src/pages/legal/PrivacyPolicy.tsx` - Company name, privacy@audiencelab.io
- `src/pages/legal/DataDeletion.tsx` - Service name, privacy@audiencelab.io

### Public HTML
- `public/index.html` - Title, meta description, Hotjar comment

### Backend
- `backend/main.py` - API title "AudienceLab API", messages, dev@audiencelab.io, service name
- `backend/auth.py` - Module comment, dev@audiencelab.io

### Config/Root
- `package.json` - name: "audiencelab", author: "AudienceLab Team"
- `README.md` - Complete rewrite for AudienceLab
- `PROJECT_OVERVIEW.md` - Title, overview, directory references

---

## Infrastructure Files Updated (Dec 11, 2025)

All infrastructure files have been updated from "sucana" to "audiencelab":

### Docker/Nginx/Supervisor (UPDATED)
- `backend/docker-compose.yml` - container_name: audiencelab-backend, network: audiencelab-network
- `nginx/app.conf` - upstream audiencelab_backend, paths /home/ubuntu/audiencelab, logs audiencelab_*.log
- `nginx/app-basic.conf` - server_name api.audiencelab.io, paths /home/ubuntu/audiencelab
- `supervisor/app.conf` - program:audiencelab-backend, paths /home/ubuntu/audiencelab

### Shell Scripts (UPDATED)
- `start-backend.sh` - paths updated to /Users/vinodsharma/code/AudienceLab
- `start-frontend.sh` - paths updated to /Users/vinodsharma/code/AudienceLab
- `start-all.sh` - paths updated to /Users/vinodsharma/code/AudienceLab
- `restart-backend.sh` - paths updated to /Users/vinodsharma/code/AudienceLab
- `start_backend.sh` - paths updated to /Users/vinodsharma/code/AudienceLab
- `backend/deploy-clean.sh` - paths updated, container names updated
- `backend/deploy-and-verify.sh` - paths updated, container names updated

### GitHub Actions (UPDATED)
- `.github/workflows/deploy-backend.yml` - paths /home/ubuntu/audiencelab, container audiencelab-backend, git repo audiencelab

### Still Need Server-Side Updates
When deploying:
1. Rename folder on Lightsail: `mv /home/ubuntu/sucana-v4 /home/ubuntu/audiencelab`
2. Update GitHub repo name if desired
3. Update DNS records for api.audiencelab.io

### CORS Origins in main.py (NOT YET UPDATED)
Still references:
- `https://app.sucana.io`
- `http://app.sucana.io`
- `https://app2.sucana.io:3000`

### Other Backend Files with "sucana" references (NOT YET UPDATED)
- `s3_service.py` - bucket name "sucana-media"
- `hedra_client.py` - User-Agent "Sucana-v4/1.0"
- Various route files have comment headers mentioning Sucana

---

## Deleted Items (This Session)

### Folders Deleted by User
- `frontend/src/pages/facebook-integration/` (entire folder)
- `frontend/src/pages/facebook-ads/` (entire folder)
- `frontend/src/pages/video-ads-v3-prototype/` (entire folder)

### Files Identified as Safe to Delete
- `src/components/BackendErrorBanner.tsx` - unused
- `src/hooks/useBackendCheck.ts` - unused
- `.bak` files in video-ads-v3-prototype (deleted with folder)

### Removed from Sidebar
- FB Connections
- FB Analytics
- FB Conversion Report

### Removed from App.tsx
- All Facebook-related imports and routes
- V3 prototype imports and routes

---

## Current Active Versions

- **V3 routes are active** in backend (`video_ads_v3_routes.py`)
- **V4 is experimental** (content library approach)
- V1/V2 are legacy

---

## Key File Locations

### Backend Core
- `backend/main.py` - FastAPI app, CORS, routes
- `backend/auth.py` - JWT verification, Supabase auth
- `backend/workflow_v2_manager.py` - 4-phase Claude pipeline
- `backend/video_ads_v3_routes.py` - Main API (99KB)
- `backend/prompts_v2/*.yaml` - Claude prompt templates

### Frontend Core
- `src/App.tsx` - Routes and theme
- `src/components/Sidebar.tsx` - Navigation
- `src/contexts/AuthContext.tsx` - Auth state
- `src/pages/video-ads-v2/*` - Main workflow UI
- `src/pages/video-ads-v4/*` - Experimental UI

---

## Environment Variables Needed

### Backend
```
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_JWT_SECRET=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
ELEVENLABS_API_KEY= (optional)
HEDRA_API_KEY= (optional)
```

### Frontend
```
REACT_APP_SUPABASE_URL=
REACT_APP_SUPABASE_ANON_KEY=
REACT_APP_API_URL=http://localhost:8000
```

---

## Commands

```bash
# Development (both frontend + backend)
npm run dev

# Frontend only
cd frontend && npm start

# Backend only
cd backend && source venv/bin/activate && python start.py

# Build
cd frontend && npm run build
```

---

## Folder Rename Status

The folder has been renamed to `AudienceLab` (working directory: `/Users/vinodsharma/code/AudienceLab`).

All local paths in scripts now reference `/Users/vinodsharma/code/AudienceLab`.
