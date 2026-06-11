"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { authApi, settingsApi } from "@/lib/api";
import type { SendTimingSettings, User } from "@/types/api";

const TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Asia/Tokyo",
  "UTC",
];

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [fullName, setFullName] = useState("");
  const [timezone, setTimezone] = useState("America/New_York");
  const [sendTiming, setSendTiming] = useState<SendTimingSettings | null>(null);
  const [accountCooldownMinutes, setAccountCooldownMinutes] = useState("30");
  const [poolGapMinMinutes, setPoolGapMinMinutes] = useState("2");
  const [poolGapMaxMinutes, setPoolGapMaxMinutes] = useState("3");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingTiming, setSavingTiming] = useState(false);
  const [message, setMessage] = useState("");
  const [timingMessage, setTimingMessage] = useState("");

  useEffect(() => {
    Promise.all([authApi.me(), settingsApi.getSendTiming()])
      .then(([userData, timing]) => {
        setUser(userData);
        setFullName(userData.full_name);
        setTimezone(userData.timezone ?? "America/New_York");
        setSendTiming(timing);
        setAccountCooldownMinutes(String(timing.account_cooldown_minutes));
        setPoolGapMinMinutes(String(timing.inter_account_delay_min_minutes));
        setPoolGapMaxMinutes(String(timing.inter_account_delay_max_minutes));
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const updated = await authApi.updateMe({ full_name: fullName, timezone });
      setUser(updated);
      setMessage("Settings saved successfully.");
    } catch {
      setMessage("Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveSendTiming(e: React.FormEvent) {
    e.preventDefault();
    setSavingTiming(true);
    setTimingMessage("");
    try {
      const cooldown = parseInt(accountCooldownMinutes, 10);
      const gapMin = parseInt(poolGapMinMinutes, 10);
      const gapMax = parseInt(poolGapMaxMinutes, 10);
      if (Number.isNaN(cooldown) || cooldown < 1) {
        setTimingMessage("Account cooldown must be at least 1 minute.");
        return;
      }
      if (Number.isNaN(gapMin) || Number.isNaN(gapMax) || gapMin > gapMax) {
        setTimingMessage("Pool gap min must be less than or equal to max.");
        return;
      }
      const updated = await settingsApi.updateSendTiming({
        account_cooldown_minutes: cooldown,
        inter_account_delay_min_minutes: gapMin,
        inter_account_delay_max_minutes: gapMax,
      });
      setSendTiming(updated);
      setTimingMessage("Saved. New timing applies to the next emails.");
    } catch (err) {
      setTimingMessage(
        err instanceof Error ? err.message : "Failed to save send timing."
      );
    } finally {
      setSavingTiming(false);
    }
  }

  if (loading) {
    return <PageLoader />;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Settings"
        description="Profile, send timing, timezone, and compliance"
      />

      <Card>
        <CardHeader>
          <CardTitle>How fast emails go out</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveSendTiming} className="space-y-4">
            <Input
              label="Wait between emails from the same account (minutes)"
              type="number"
              min={1}
              max={240}
              value={accountCooldownMinutes}
              onChange={(e) => setAccountCooldownMinutes(e.target.value)}
              hint="Default is 30 minutes. Helps avoid looking like spam to Gmail."
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Shortest pause between accounts (minutes)"
                type="number"
                min={1}
                max={60}
                value={poolGapMinMinutes}
                onChange={(e) => setPoolGapMinMinutes(e.target.value)}
              />
              <Input
                label="Longest pause between accounts (minutes)"
                type="number"
                min={1}
                max={60}
                value={poolGapMaxMinutes}
                onChange={(e) => setPoolGapMaxMinutes(e.target.value)}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              When you use several Gmail accounts, the system switches between them
              with a short break (about {sendTiming?.inter_account_delay_min_minutes}–
              {sendTiming?.inter_account_delay_max_minutes} minutes).
            </p>
            {timingMessage && (
              <Alert
                variant={
                  timingMessage.includes("Saved") ? "success" : "danger"
                }
                onDismiss={() => setTimingMessage("")}
              >
                {timingMessage}
              </Alert>
            )}
            <Button type="submit" loading={savingTiming}>
              Save email timing
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <Input label="Email" value={user?.email ?? ""} disabled />
            <Input
              label="Full name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
            <Select
              label="Timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              hint="Used for campaign send windows and scheduling"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </Select>
            {message && (
              <Alert
                variant={message.includes("success") ? "success" : "danger"}
                onDismiss={() => setMessage("")}
              >
                {message}
              </Alert>
            )}
            <Button type="submit" loading={saving}>
              Save changes
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Compliance notice</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <p>
            You are solely responsible for compliance with applicable laws
            (CAN-SPAM, GDPR, CASL, etc.) and Google Terms of Service. This
            platform enforces technical guardrails including unsubscribe links,
            suppression lists, and send rate limits — but does not provide legal
            advice.
          </p>
          <p className="mt-3">
            All outreach emails must include a physical mailing address and
            working unsubscribe mechanism as required by CAN-SPAM.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
