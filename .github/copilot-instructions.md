<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Sucana v4 Development Guidelines

This is a modern full-stack web application with authentication and dashboard functionality.

## Project Structure
- **Backend**: Python FastAPI with Supabase authentication
- **Frontend**: React with TypeScript and Material-UI
- **Features**: Clean, minimal setup with login and dashboard

## Key Technologies
- FastAPI with Supabase JWT authentication
- React with TypeScript
- Material-UI for UI components
- Supabase for authentication and database

## Development Guidelines
- Use TypeScript for type safety
- Follow Material-UI design patterns
- Implement proper error handling
- Use modern React hooks and functional components
- Keep components focused and reusable

## Code Style
- Use arrow functions for components
- Implement proper loading states
- Include error boundaries
- Use meaningful variable names
- Add TypeScript interfaces for data structures

## Authentication
- All protected routes use Supabase JWT tokens
- Backend verifies tokens using Supabase secret
- Frontend uses Supabase client for auth operations

## API Design
- RESTful endpoints
- Proper HTTP status codes
- Consistent error response format
- JWT bearer token authentication
