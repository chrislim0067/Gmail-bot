"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { gmailApi, ApiClientError } from "@/lib/api";

// React Strict Mode mounts twice in dev; OAuth state is single-use.
const mockConnectInflight = new Map<
  string,
  Promise<{ id: string; email: string; status: string }>
>();

function mockConnectOnce(state: string) {
  const existing = mockConnectInflight.get(state);
  if (existing) {
    return existing;
  }
  const request = gmailApi.mockConnect(state);
  mockConnectInflight.set(state, request);
  return request;
}

export default function MockConnectPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const state = searchParams.get("state");
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    if (!state) {
      setError("Missing OAuth state. Start again from Connect Gmail.");
      return;
    }

    let cancelled = false;

    mockConnectOnce(state)
      .then((account) => {
        if (cancelled) return;
        setEmail(account.email);
        router.replace("/accounts?connected=1");
      })
      .catch(async (err) => {
        if (cancelled) return;

        if (
          err instanceof ApiClientError &&
          err.status === 400 &&
          /invalid or expired oauth state/i.test(err.message)
        ) {
          try {
            const data = await gmailApi.listAccounts();
            if (data.items.length > 0) {
              router.replace("/accounts?connected=1");
              return;
            }
          } catch {
            // fall through to error UI
          }
        }

        if (err instanceof ApiClientError) {
          setError(err.message);
        } else {
          setError("Could not connect mock Gmail account.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [state, router]);

  if (error) {
    return (
      <div className="mx-auto max-w-lg pt-12">
        <Card>
          <CardContent className="space-y-4 pt-6">
            <p className="text-sm text-red-700">{error}</p>
            <p className="text-sm text-slate-600">
              If you already connected, open Accounts to check your inbox list.
            </p>
            <div className="flex gap-2">
              <Button onClick={() => router.push("/accounts/connect")}>
                Try again
              </Button>
              <Button variant="outline" onClick={() => router.push("/accounts")}>
                View accounts
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-4 pt-16 text-center">
      <Loader2 className="h-8 w-8 animate-spin text-brand" />
      <div>
        <h1 className="text-lg font-semibold text-slate-900">
          Connecting mock Gmail account
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {email
            ? `Connected ${email}. Redirecting...`
            : "Please wait while we finish setup..."}
        </p>
      </div>
    </div>
  );
}
