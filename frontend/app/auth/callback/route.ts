import { NextRequest, NextResponse } from 'next/server';
import {
  exchangeCodeForTokens,
  getAppUrl,
  verifyCognitoToken,
  decodeOAuthState,
  isSafeReturnPath,
  SESSION_COOKIE,
  REFRESH_COOKIE,
  STATE_COOKIE,
} from '@/lib/auth';

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get('code');
  const stateParam = request.nextUrl.searchParams.get('state') || '';
  const appUrl = getAppUrl(request);

  if (!code) {
    return NextResponse.redirect(`${appUrl}/?error=missing_code`);
  }

  // CSRF: verify the state nonce matches the cookie
  const storedNonce = request.cookies.get(STATE_COOKIE)?.value;
  const decoded = decodeOAuthState(stateParam);

  if (!storedNonce || !decoded || decoded.nonce !== storedNonce) {
    const response = NextResponse.redirect(`${appUrl}/?error=invalid_state`);
    response.cookies.delete(STATE_COOKIE);
    return response;
  }

  const returnTo = isSafeReturnPath(decoded.returnTo) ? decoded.returnTo : '/';

  try {
    const tokens = await exchangeCodeForTokens(code, appUrl);
    await verifyCognitoToken(tokens.id_token);

    const response = NextResponse.redirect(`${appUrl}${returnTo}`);
    response.cookies.delete(STATE_COOKIE);
    response.cookies.set(SESSION_COOKIE, tokens.id_token, {
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
      path: '/',
      maxAge: 3600,
    });
    if (tokens.refresh_token) {
      response.cookies.set(REFRESH_COOKIE, tokens.refresh_token, {
        httpOnly: true,
        secure: true,
        sameSite: 'lax',
        path: '/',
        maxAge: 36000,
      });
    }
    return response;
  } catch (err) {
    console.error('Auth callback error:', err instanceof Error ? err.message : 'Unknown error');
    const response = NextResponse.redirect(`${appUrl}/?error=auth_failed`);
    response.cookies.delete(STATE_COOKIE);
    return response;
  }
}
