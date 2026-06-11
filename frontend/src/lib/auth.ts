import { authApi } from "@/lib/api";
import type { User } from "@/types/api";

const TOKEN_KEY = "access_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function register(
  email: string,
  password: string,
  fullName?: string
): Promise<User> {
  await authApi.register(email, password, fullName);
  return login(email, password);
}

export async function login(
  email: string,
  password: string
): Promise<User> {
  const response = await authApi.login(email, password);
  setStoredToken(response.access_token);
  return authApi.me();
}

export async function logout(): Promise<void> {
  try {
    await authApi.logout();
  } finally {
    clearStoredToken();
  }
}

export async function getCurrentUser(): Promise<User | null> {
  if (!getStoredToken()) {
    return null;
  }

  try {
    return await authApi.me();
  } catch {
    clearStoredToken();
    return null;
  }
}

export function isAuthenticated(): boolean {
  return !!getStoredToken();
}

export function redirectToLogin(options?: { expired?: boolean; next?: string }): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams();
  if (options?.expired) params.set("expired", "1");
  if (options?.next) params.set("next", options.next);
  const query = params.toString();
  window.location.href = query ? `/login?${query}` : "/login";
}

export function redirectAfterAuth(next?: string | null): void {
  if (typeof window === "undefined") return;
  const dest = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
  window.location.href = dest;
}

export function redirectToDashboard(): void {
  redirectAfterAuth("/");
}
