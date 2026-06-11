"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { register, redirectToDashboard } from "@/lib/auth";
import { ApiClientError } from "@/lib/api";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await register(email, password, fullName || undefined);
      redirectToDashboard();
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Unable to create account. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Set up operator access for Gmail Outreach"
    >
      <div className="glass-panel gradient-border p-8 sm:p-10">
        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            label="Full name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Your name"
            autoComplete="name"
          />
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
            placeholder="Min 8 chars, 1 uppercase, 1 number"
            required
            autoComplete="new-password"
          />
          {error && (
            <Alert variant="danger" onDismiss={() => setError("")}>
              {error}
            </Alert>
          )}
          <Button type="submit" className="w-full" size="lg" loading={loading}>
            Create account
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-semibold text-brand transition-colors hover:text-brand-rose"
            >
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </AuthLayout>
  );
}
