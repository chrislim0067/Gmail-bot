"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Copy, ExternalLink, Shield } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
import { getGmailConnectUrl, gmailApi } from "@/lib/api";

type ConnectInfo = {
  use_mock_gmail: boolean;
  oauth_publishing_status: string;
  redirect_uri: string;
  redirect_uris_for_google_console: string[];
  google_client_id: string;
  google_client_configured: boolean;
  google_client_edit_url: string;
};

export default function ConnectGmailPage() {
  const [info, setInfo] = useState<ConnectInfo | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    gmailApi.connectInfo().then(setInfo).catch(() => null);
  }, []);

  function handleConnect() {
    window.location.href = getGmailConnectUrl();
  }

  async function copyText(text: string) {
    await navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(null), 2000);
  }

  const redirectUris =
    info?.redirect_uris_for_google_console ?? [
      "http://localhost:8000/api/v1/gmail/callback",
      "http://127.0.0.1:8000/api/v1/gmail/callback",
    ];

  const readyForReal =
    info !== null && !info.use_mock_gmail && info.google_client_configured;
  const needsSetup =
    info === null || info.use_mock_gmail || !info.google_client_configured;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Connect Gmail"
        description="Connect your real Gmail account via Google sign-in"
      />

      {needsSetup && (
        <Card className="border-brand/30">
          <CardHeader>
            <CardTitle>One-time Google setup</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-foreground">
            <p>
              Real Gmail requires OAuth credentials from Google Cloud (free,
              ~5 minutes). Run this on your PC:
            </p>
            <code className="block rounded-lg bg-zinc-900 px-4 py-3 text-xs text-emerald-400">
              bin\GmailOutreach-ConfigureGoogle.bat
            </code>
            <ol className="list-decimal space-y-2 pl-5">
              <li>
                Enable{" "}
                <a
                  href="https://console.cloud.google.com/apis/library/gmail.googleapis.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand underline"
                >
                  Gmail API
                </a>
              </li>
              <li>
                OAuth consent screen → External → Testing → add your Gmail as{" "}
                <strong>Test user</strong>
              </li>
              <li>
                In your OAuth client, add these under{" "}
                <strong>Authorized redirect URIs</strong> (not JavaScript
                origins):
                <div className="mt-2 space-y-2">
                  {redirectUris.map((uri) => (
                    <div key={uri} className="flex items-center gap-2">
                      <code className="flex-1 rounded bg-zinc-100 px-2 py-1 text-xs">
                        {uri}
                      </code>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => copyText(uri)}
                      >
                        <Copy className="h-3.5 w-3.5" />
                        {copied === uri ? "Copied" : "Copy"}
                      </Button>
                    </div>
                  ))}
                </div>
              </li>
              <li>
                Paste Client ID + Secret into{" "}
                <code className="rounded bg-zinc-100 px-1">
                  GmailOutreach-ConfigureGoogle.bat
                </code>
              </li>
              <li>
                Restart:{" "}
                <code className="rounded bg-zinc-100 px-1">Stop.bat</code> then{" "}
                <code className="rounded bg-zinc-100 px-1">Start.bat</code>
              </li>
            </ol>
            <a
              href="https://console.cloud.google.com/apis/credentials"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-brand underline"
            >
              Open Google Cloud Console
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </CardContent>
        </Card>
      )}

      {readyForReal && (
        <Alert variant="danger" title='Getting "redirect_uri_mismatch"?'>
          <p>
            Your app sends this exact redirect URI to Google. It must appear
            under <strong>Authorized redirect URIs</strong> on your OAuth
            client — then click <strong>Save</strong> and wait 2 minutes.
          </p>
          <div className="mt-3 space-y-2">
            {redirectUris.map((uri) => (
              <div key={uri} className="flex items-center gap-2">
                <code className="flex-1 rounded bg-white/80 px-2 py-1 text-xs">
                  {uri}
                </code>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => copyText(uri)}
                >
                  <Copy className="h-3.5 w-3.5" />
                  {copied === uri ? "Copied" : "Copy"}
                </Button>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs">
            Client ID:{" "}
            <code className="rounded bg-white/80 px-1">{info?.google_client_id}</code>
          </p>
          {info?.google_client_edit_url && (
            <a
              href={info.google_client_edit_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 font-medium text-brand underline"
            >
              Open your OAuth client in Google Console
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </Alert>
      )}

      {readyForReal && info?.oauth_publishing_status === "testing" && (
        <Alert variant="warning" title="Testing mode">
          Each Gmail you connect must be added as a Test user in Google Cloud
          Console.
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {readyForReal ? (
              <CheckCircle2 className="h-5 w-5 text-success" />
            ) : (
              <Shield className="h-5 w-5 text-brand" />
            )}
            {readyForReal ? "Ready to connect" : "Google OAuth connection"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            You will sign in with Google and grant{" "}
            <code className="rounded bg-zinc-100 px-1">gmail.send</code> and{" "}
            <code className="rounded bg-zinc-100 px-1">gmail.readonly</code>.
            Tokens are encrypted at rest.
          </p>

          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>• Only Gmail accounts you own should be connected</li>
            <li>• Start with low send volume (tier caps apply automatically)</li>
            <li>• You can revoke access anytime from Accounts</li>
          </ul>

          <Alert variant="warning" title="Compliance notice">
            You are solely responsible for CAN-SPAM, GDPR, and Google Terms of
            Service compliance.
          </Alert>

          <Button
            onClick={handleConnect}
            className="w-full sm:w-auto"
            disabled={!readyForReal}
          >
            <ExternalLink className="h-4 w-4" />
            Connect with Google
          </Button>

          {!readyForReal && (
            <p className="text-xs text-muted-foreground">
              Complete the one-time Google setup above, then restart the app.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
