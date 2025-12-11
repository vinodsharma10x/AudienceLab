// Utility for smart token handling
// Tries JWT token first, falls back to dev-token if JWT is expired or invalid

interface Session {
  access_token?: string;
  token_type?: string;
  expires_in?: number;
  expires_at?: number;
  refresh_token?: string;
  user?: any;
}

export const getValidToken = (session: Session | null): string => {
  // If no session, use dev-token
  if (!session?.access_token) {
    return 'dev-token';
  }

  // Check if JWT token is expired
  try {
    const payload = JSON.parse(atob(session.access_token.split('.')[1]));
    const now = Math.floor(Date.now() / 1000);
    
    if (payload.exp && payload.exp < now) {
      console.warn('⚠️ JWT token expired, using dev-token');
      return 'dev-token';
    }
    
    // Token is valid
    return session.access_token;
  } catch (e) {
    console.warn('⚠️ Failed to parse JWT token, using dev-token');
    return 'dev-token';
  }
};

export const makeAuthenticatedRequest = async (
  url: string, 
  options: RequestInit, 
  session: Session | null
) => {
  const token = getValidToken(session);
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  };

  return fetch(url, {
    ...options,
    headers,
  });
};
