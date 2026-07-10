import { NextRequest, NextResponse } from 'next/server';
import { verifyCognitoToken, refreshCognitoTokens, SESSION_COOKIE, REFRESH_COOKIE } from './lib/auth';

const PROTECTED_PAGES = ['/create', '/print'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPage = PROTECTED_PAGES.includes(pathname);

  const token = request.cookies.get(SESSION_COOKIE)?.value;

  if (!token) {
    // ID token cookie expired — try refresh before redirecting
    const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
    if (refreshToken) {
      try {
        const tokens = await refreshCognitoTokens(refreshToken);
        const payload = await verifyCognitoToken(tokens.id_token);

        const headers = new Headers(request.headers);
        headers.set('x-user-sub', payload.sub ?? '');
        if (payload.email) headers.set('x-user-email', payload.email);
        headers.set('authorization', `Bearer ${tokens.id_token}`);

        const response = NextResponse.next({ request: { headers } });
        response.cookies.set(SESSION_COOKIE, tokens.id_token, {
          httpOnly: true,
          secure: true,
          sameSite: 'lax',
          path: '/',
          maxAge: 3600,
        });
        return response;
      } catch {
        // Refresh failed — fall through to login redirect
      }
    }

    if (isPage) {
      const loginUrl = new URL('/auth/login', request.url);
      loginUrl.searchParams.set('return_to', pathname + request.nextUrl.search);
      const response = NextResponse.redirect(loginUrl);
      response.cookies.delete(REFRESH_COOKIE);
      return response;
    }
    return NextResponse.json(
      { error: 'Missing authorization token' },
      { status: 401, headers: { 'WWW-Authenticate': 'Bearer' } },
    );
  }

  try {
    const payload = await verifyCognitoToken(token);

    const headers = new Headers(request.headers);
    headers.set('x-user-sub', payload.sub ?? '');
    if (payload.email) headers.set('x-user-email', payload.email);
    headers.set('authorization', `Bearer ${token}`);

    return NextResponse.next({ request: { headers } });
  } catch {
    // Token expired or invalid — attempt silent refresh
    const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
    if (refreshToken) {
      try {
        const tokens = await refreshCognitoTokens(refreshToken);
        const payload = await verifyCognitoToken(tokens.id_token);

        const headers = new Headers(request.headers);
        headers.set('x-user-sub', payload.sub ?? '');
        if (payload.email) headers.set('x-user-email', payload.email);
        headers.set('authorization', `Bearer ${tokens.id_token}`);

        const response = NextResponse.next({ request: { headers } });
        response.cookies.set(SESSION_COOKIE, tokens.id_token, {
          httpOnly: true,
          secure: true,
          sameSite: 'lax',
          path: '/',
          maxAge: 3600,
        });
        return response;
      } catch {
        // Refresh also failed — fall through to login redirect
      }
    }

    if (isPage) {
      const loginUrl = new URL('/auth/login', request.url);
      loginUrl.searchParams.set('return_to', pathname);
      const response = NextResponse.redirect(loginUrl);
      response.cookies.delete(SESSION_COOKIE);
      response.cookies.delete(REFRESH_COOKIE);
      return response;
    }
    return NextResponse.json(
      { error: 'Invalid or expired token' },
      { status: 401, headers: { 'WWW-Authenticate': 'Bearer' } },
    );
  }
}

export const config = {
  matcher: [
    '/create',
    '/print',
    '/api/((?!health).*)',
  ],
};
