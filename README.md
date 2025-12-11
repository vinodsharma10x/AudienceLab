# AudienceLab

A marketing research and content generation platform that helps you understand your audience and create resonant messaging.

## Features

- **Audience Research**: AI-powered analysis of your target audience
- **Avatar Analysis**: Build detailed customer personas with demographics, psychographics, and pain points
- **Journey Mapping**: Understand your customer's decision-making process
- **Objections Analysis**: Identify and address purchase barriers
- **Marketing Angles**: Generate strategic marketing approaches
- **Hooks Generation**: Create attention-grabbing hooks
- **Scripts Generation**: Produce compelling marketing scripts
- **Authentication**: Secure login/signup with Supabase

## Tech Stack

- **Frontend**: React 19, TypeScript, Material-UI
- **Backend**: FastAPI, Python
- **AI**: Claude (Anthropic) for content generation, OpenAI for URL parsing
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth

## Setup Instructions

### Prerequisites
- Node.js 18+
- Python 3.8+
- Supabase account

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python start.py
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with your credentials
npm start
```

### Run Both (Development)

```bash
npm run dev
```

## Environment Variables

### Backend (.env)
```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_JWT_SECRET=your_jwt_secret
ANTHROPIC_API_KEY=your_claude_key
OPENAI_API_KEY=your_openai_key
```

### Frontend (.env)
```
REACT_APP_SUPABASE_URL=your_supabase_url
REACT_APP_SUPABASE_ANON_KEY=your_anon_key
REACT_APP_API_URL=http://localhost:8000
```

## License

MIT License
