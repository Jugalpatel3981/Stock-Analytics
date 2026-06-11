import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { AuthUser } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/env";

export async function requireAuthenticatedUser(): Promise<AuthUser> {
  const cookieHeader = (await cookies()).toString();

  if (!cookieHeader) {
    redirect("/login");
  }

  const response = await fetch(`${getApiBaseUrl()}/auth/me`, {
    headers: {
      Cookie: cookieHeader,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    redirect("/login");
  }

  return response.json() as Promise<AuthUser>;
}

export async function getAuthCookieHeader(): Promise<string> {
  return (await cookies()).toString();
}
