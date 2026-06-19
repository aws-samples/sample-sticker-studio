import { NextRequest, NextResponse } from 'next/server';
import { buildLogoutUrl, getAppUrl, SESSION_COOKIE, REFRESH_COOKIE } from '@/lib/auth';

export async function GET(request: NextRequest) {
  const response = NextResponse.redirect(buildLogoutUrl(getAppUrl(request)));
  response.cookies.delete(SESSION_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  return response;
}
