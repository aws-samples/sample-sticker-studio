import { createRemoteJWKSet, jwtVerify, JWTPayload } from 'jose';
import { cookies } from 'next/headers';
import { randomBytes } from 'crypto';
import { NextRequest } from 'next/server';

export interface CognitoIdToken extends JWTPayload {
  token_use?: string;
  'cognito:groups'?: string[];
  email?: string;
}

const SESSION_COOKIE = '__session_id_token';
const REFRESH_COOKIE = '__session_refresh_token';
const STATE_COOKIE = '__oauth_state';

function getConfig() {
  return {
    region: process.env.NEXT_PUBLIC_COGNITO_REGION!,
    userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
    clientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
    clientSecret: process.env.COGNITO_CLIENT_SECRET,
    domain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN!,
  };
}

/** Derive the app URL from the incoming request's Host header. */
export function getAppUrl(request: NextRequest): string {
  const host = request.headers.get('x-forwarded-host') || request.headers.get('host');
  if (host) {
    // Always use HTTPS for non-localhost hosts (CloudFront terminates TLS,
    // so x-forwarded-proto from the origin may incorrectly report "http")
    const proto = host.startsWith('localhost') ? 'http' : 'https';
    return `${proto}://${host}`;
  }
  return process.env.APP_URL!;
}

function getIssuer() {
  const { region, userPoolId } = getConfig();
  return `https://cognito-idp.${region}.amazonaws.com/${userPoolId}`;
}

let jwks: ReturnType<typeof createRemoteJWKSet> | null = null;
function getJWKS() {
  if (!jwks) {
    jwks = createRemoteJWKSet(new URL(`${getIssuer()}/.well-known/jwks.json`));
  }
  return jwks;
}

export async function verifyCognitoToken(token: string): Promise<CognitoIdToken> {
  const { clientId } = getConfig();
  const { payload } = await jwtVerify<CognitoIdToken>(token, getJWKS(), {
    issuer: getIssuer(),
    audience: clientId,
    algorithms: ['RS256'],
  });
  if (payload.token_use !== 'id') {
    throw new Error('Invalid token_use: expected id token');
  }
  return payload;
}

/** Generate a random nonce for OAuth state CSRF protection. */
export function generateOAuthNonce(): string {
  return randomBytes(32).toString('hex');
}

/** Encode the OAuth state parameter as nonce:returnTo. */
function encodeOAuthState(nonce: string, returnTo: string): string {
  return `${nonce}:${returnTo}`;
}

/** Decode the OAuth state parameter. Returns null if malformed. */
export function decodeOAuthState(state: string): { nonce: string; returnTo: string } | null {
  const idx = state.indexOf(':');
  if (idx === -1) return null;
  return { nonce: state.slice(0, idx), returnTo: state.slice(idx + 1) };
}

/** Validate that a return path is a safe relative path (no open redirect). */
export function isSafeReturnPath(path: string): boolean {
  return path.startsWith('/') && !path.startsWith('//');
}

/** Build the Cognito hosted-UI authorize URL. Nonce must be stored in a cookie by the caller. */
export function buildLoginUrl(nonce: string, returnTo = '/', appUrl: string) {
  const { domain, region, clientId } = getConfig();
  const redirectUri = encodeURIComponent(`${appUrl}/auth/callback`);
  const state = encodeURIComponent(encodeOAuthState(nonce, returnTo));
  return (
    `https://${domain}.auth.${region}.amazoncognito.com/oauth2/authorize` +
    `?response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&scope=email+openid&state=${state}`
  );
}

/** Build the Cognito logout URL. Clears the Cognito hosted UI session,
 * then redirects the user to the app root via logout_uri. */
export function buildLogoutUrl(appUrl: string) {
  const { domain, region, clientId } = getConfig();
  return (
    `https://${domain}.auth.${region}.amazoncognito.com/logout` +
    `?client_id=${clientId}&logout_uri=${encodeURIComponent(appUrl)}`
  );
}

/** Exchange an authorization code for tokens via Cognito's token endpoint. */
export async function exchangeCodeForTokens(code: string, appUrl: string) {
  const { domain, region, clientId, clientSecret } = getConfig();
  const tokenUrl = `https://${domain}.auth.${region}.amazoncognito.com/oauth2/token`;

  const params = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    client_id: clientId,
    redirect_uri: `${appUrl}/auth/callback`,
  });

  const headers: Record<string, string> = {
    'Content-Type': 'application/x-www-form-urlencoded',
  };

  // If a client secret is configured, use Basic auth
  if (clientSecret) {
    headers['Authorization'] =
      'Basic ' + Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
  }

  const res = await fetch(tokenUrl, {
    method: 'POST',
    headers,
    body: params.toString(),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Token exchange failed (${res.status}): ${body}`);
  }

  return res.json() as Promise<{ id_token: string; access_token: string; refresh_token?: string }>;
}

/** Use a refresh token to obtain new tokens from Cognito. */
export async function refreshCognitoTokens(refreshToken: string) {
  const { domain, region, clientId } = getConfig();
  const tokenUrl = `https://${domain}.auth.${region}.amazoncognito.com/oauth2/token`;

  const params = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: clientId,
  });

  const res = await fetch(tokenUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params.toString(),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Token refresh failed (${res.status}): ${body}`);
  }

  return res.json() as Promise<{ id_token: string; access_token: string }>;
}

/** Read the session token from the httpOnly cookie. */
export async function getSessionToken(): Promise<string | null> {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE)?.value ?? null;
}

/** Get the verified user payload from the session cookie, or null. */
export async function getSession(): Promise<CognitoIdToken | null> {
  const token = await getSessionToken();
  if (!token) return null;
  try {
    return await verifyCognitoToken(token);
  } catch {
    return null;
  }
}

export { SESSION_COOKIE, REFRESH_COOKIE, STATE_COOKIE };
