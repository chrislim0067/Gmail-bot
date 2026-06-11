"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { login, redirectAfterAuth } from "@/lib/auth";
import { ApiClientError } from "@/lib/api";

function LoginForm() {
  const searchParams = useSearchParams();
  const sessionExpired = searchParams.get("expired") === "1";
  const returnTo = searchParams.get("next");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      redirectAfterAuth(returnTo);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Unable to sign in. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to continue to your dashboard">
      <div className="glass-panel gradient-border p-8 sm:p-10">
        <form onSubmit={handleSubmit} className="space-y-5">
          {sessionExpired && (
            <Alert variant="warning">
              Your session expired. Please sign in again.
            </Alert>
          )}
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            required
            autoComplete="email"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            required
            autoComplete="current-password"
          />
          {error && (
            <Alert variant="danger" onDismiss={() => setError("")}>
              {error}
            </Alert>
          )}
          <Button type="submit" className="w-full" size="lg" loading={loading}>
            Sign in
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            No account yet?{" "}
            <Link
              href="/register"
              className="font-semibold text-brand transition-colors hover:text-brand-rose"
            >
              Create one
            </Link>
          </p>
        </form>
      </div>
    </AuthLayout>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
