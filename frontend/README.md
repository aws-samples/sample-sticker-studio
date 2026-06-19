# Sticker Studio — Frontend

Next.js 15 app (App Router) that provides the UI for creating, previewing, and downloading AI-generated stickers. Runs in standalone mode on ECS Fargate behind CloudFront.

## Pages

| Route | Auth | Description |
|---|---|---|
| `/` | No | Welcome / landing page with login prompt |
| `/about` | No | About page |
| `/create` | Yes | Design studio — pick character + activity + location, generate sticker |
| `/print` | Yes | Preview a generated sticker and download as PNG |
| `/auth/login` | — | Redirects to Cognito hosted UI |
| `/auth/callback` | — | Handles OAuth authorization code exchange |
| `/auth/logout` | — | Clears session and redirects to Cognito logout |
| `/api/health` | No | Health check endpoint (used by ALB target group) |

## Auth Flow

Authentication uses Cognito OAuth 2.0 (authorization code grant). The middleware (`middleware.ts`) protects `/create`, `/print`, and all `/api/*` routes (except `/api/health`):

1. Checks for an `id_token` in an httpOnly cookie
2. If expired, attempts a silent refresh using the refresh token cookie
3. If both fail, redirects to `/auth/login` (for pages) or returns 401 (for API routes)

Tokens are verified server-side using Cognito's JWKS endpoint via the `jose` library.

## Sticker Generation

The `/create` page lets users:
- Select from predefined characters, activities, and locations (with search/filter)
- Or type custom prompts for any category
- Hit "Generate" which calls a server action (`lib/actions/generate.ts`)
- The server action sends the request to API Gateway with the user's Cognito ID token
- 3 sticker variants are returned as S3 presigned URLs
- User picks one and navigates to `/print` to download it

## Development

```bash
npm ci
npm run dev        # http://localhost:3000
```

Requires these env vars to be set (injected by Fargate in deployed environments):

```
NEXT_PUBLIC_COGNITO_REGION
NEXT_PUBLIC_COGNITO_USER_POOL_ID
NEXT_PUBLIC_COGNITO_CLIENT_ID
NEXT_PUBLIC_COGNITO_DOMAIN
NEXT_PUBLIC_API_URL
```

## Docker

The Dockerfile uses a two-stage build:
- Builder: installs native deps (cairo, pango for the `canvas` npm package), runs `npm run build`
- Runner: minimal Alpine image, non-root user, copies standalone output only

```bash
docker build -t sticker-studio-frontend .
docker run -p 3000:3000 sticker-studio-frontend
```

## Tests

```bash
npm run test:run   # single run with vitest
npm run lint       # eslint
```
