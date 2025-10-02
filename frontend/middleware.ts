import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const ADMIN_PREFIX = "/admin";
const LOGIN_PATH = "/admin/login";

const getTokenFromAuthorization = (header: string | null) => {
  if (!header) {
    return null;
  }
  const match = header.match(/^Bearer\s+(.+)$/i);
  return match ? (match[1]?.trim() ?? null) : null;
};

const isAdminPath = (pathname: string) =>
  pathname === ADMIN_PREFIX || pathname.startsWith(`${ADMIN_PREFIX}/`);

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!isAdminPath(pathname) || pathname === LOGIN_PATH) {
    return NextResponse.next();
  }

  const requiredToken = process.env.ADMIN_UI_TOKEN?.trim();
  if (!requiredToken) {
    return NextResponse.next();
  }

  const cookieToken = request.cookies.get("admin_token")?.value;
  const headerToken = getTokenFromAuthorization(request.headers.get("authorization"));
  if (cookieToken === requiredToken || headerToken === requiredToken) {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = LOGIN_PATH;
  const response = NextResponse.redirect(loginUrl, { status: 307 });
  response.headers.set("x-admin-auth", "unauthorized");
  return response;
}

export const config = {
  matcher: ["/admin/:path*"],
};
