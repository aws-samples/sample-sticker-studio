import { NextRequest, NextResponse } from 'next/server';
import { buildLoginUrl, generateOAuthNonce, getAppUrl, isSafeReturnPath, STATE_COOKIE } from '@/lib/auth';

export async function GET(request: NextRequest) {
  const returnTo = request.nextUrl.searchParams.get('return_to') || '/';
  const safePath = isSafeReturnPath(returnTo) ? returnTo : '/';

  const nonce = generateOAuthNonce();
  const appUrl = getAppUrl(request);
  const response = NextResponse.redirect(buildLoginUrl(nonce, safePath, appUrl));
  response.cookies.set(STATE_COOKIE, nonce, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 300, // 5 minutes — enough to complete the login flow
  });
  return response;
}
