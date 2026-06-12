import type { ApiError } from "@/types/api";

function isLocalhostUrl(url: string): boolean {
  return /localhost|127\.0\.0\.1/i.test(url);
}

function resolveApiUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();

  if (typeof window !== "undefined") {
    const onLocalSite =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1";

    if (configured && !(isLocalhostUrl(configured) && !onLocalSite)) {
      return configured;
    }

    return `${window.location.origin}/_/backend/api/v1`;
  }

  if (configured) {
    return configured;
  }

  return "http://localhost:8000/api/v1";
}

const TOKEN_KEY = "access_token";

let sessionRedirectStarted = false;

function isAuthEndpoint(path: string): boolean {
  const normalized = path.replace(/^https?:\/\/[^/]+/, "");
  return (
    normalized.startsWith("/auth/login") ||
    normalized.startsWith("/auth/register")
  );
}

function beginSessionExpiredRedirect(): void {
  if (sessionRedirectStarted || typeof window === "undefined") return;
  sessionRedirectStarted = true;
  localStorage.removeItem(TOKEN_KEY);
  const returnPath = window.location.pathname + window.location.search;
  const next = encodeURIComponent(returnPath);
  window.location.assign(`/login?expired=1&next=${next}`);
}

export function isUnauthorizedError(err: unknown): err is ApiClientError {
  return err instanceof ApiClientError && err.status === 401;
}

export class ApiClientError extends Error {
  status: number;
  code?: string;
  errors?: string[];

  constructor(status: number, body: ApiError) {
    super(body.detail || "Request failed");
    this.name = "ApiClientError";
    this.status = status;
    this.code = body.code;
    this.errors = body.errors;
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
}

function buildUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>
): string {
  const url = new URL(
    path.startsWith("http") ? path : `${resolveApiUrl()}${path.startsWith("/") ? path : `/${path}`}`
  );

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return url.toString();
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, params, headers, ...rest } = options;

  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      ...rest,
      credentials: "include",
      headers: {
        ...(body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      body:
        body instanceof FormData
          ? body
          : body !== undefined
            ? JSON.stringify(body)
            : undefined,
    });
  } catch {
    const isLocal =
      typeof window !== "undefined" &&
      (window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1");

    throw new ApiClientError(0, {
      detail: isLocal
        ? "Cannot reach the API server. Make sure GmailOutreach-Start.bat is running (API on port 8000)."
        : "Cannot reach the API server. Check Vercel deployment and remove localhost from NEXT_PUBLIC_API_URL.",
      code: "network_error",
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    if (response.status === 401 && !isAuthEndpoint(path)) {
      if (
        typeof window !== "undefined" &&
        !window.location.pathname.startsWith("/login") &&
        !window.location.pathname.startsWith("/register")
      ) {
        beginSessionExpiredRedirect();
        throw new ApiClientError(401, {
          detail: "Session expired. Please sign in again.",
          code: "session_expired",
        });
      }
    }

    if (isJson) {
      const errorBody = (await response.json()) as ApiError;
      throw new ApiClientError(response.status, errorBody);
    }
    throw new ApiClientError(response.status, {
      detail:
        response.status >= 500
          ? "API server error. Check Vercel env vars (DATABASE_URL, JWT_SECRET, REDIS_URL)."
          : response.statusText || "Request failed",
    });
  }

  if (!isJson) {
    return response as unknown as T;
  }

  return response.json() as Promise<T>;
}

export function getApiBaseUrl(): string {
  return resolveApiUrl();
}

export function getGmailConnectUrl(): string {
  return `${resolveApiUrl()}/gmail/connect`;
}

// Auth
export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    apiFetch<import("@/types/api").User>("/auth/register", {
      method: "POST",
      body: { email, password, full_name },
    }),
  login: (email: string, password: string) =>
    apiFetch<{ access_token: string; token_type: string; expires_in: number }>(
      "/auth/login",
      { method: "POST", body: { email, password } }
    ),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
  me: () => apiFetch<import("@/types/api").User>("/auth/me"),
  updateMe: (data: { full_name?: string; timezone?: string }) =>
    apiFetch<import("@/types/api").User>("/auth/me", {
      method: "PATCH",
      body: data,
    }),
};

// Gmail accounts
export const gmailApi = {
  listAccounts: () =>
    apiFetch<{ items: import("@/types/api").GmailAccount[] }>("/gmail/accounts"),
  getAccount: (id: string) =>
    apiFetch<import("@/types/api").GmailAccountDetail>(`/gmail/accounts/${id}`),
  updateAccount: (
    id: string,
    data: { daily_send_limit?: number; hourly_send_limit?: number }
  ) =>
    apiFetch<import("@/types/api").GmailAccount>(`/gmail/accounts/${id}`, {
      method: "PATCH",
      body: data,
    }),
  pauseAccount: (id: string, reason = "manual") =>
    apiFetch<{ status: string }>(`/gmail/accounts/${id}/pause`, {
      method: "POST",
      body: { reason },
    }),
  resumeAccount: (id: string) =>
    apiFetch<{ status: string }>(`/gmail/accounts/${id}/resume`, {
      method: "POST",
    }),
  reviewAccount: (
    id: string,
    data: { approved: boolean; notes?: string; new_tier?: string }
  ) =>
    apiFetch<import("@/types/api").GmailAccount>(`/gmail/accounts/${id}/review`, {
      method: "POST",
      body: data,
    }),
  setTier: (id: string, account_tier: string, reason: string) =>
    apiFetch<import("@/types/api").GmailAccount>(
      `/gmail/accounts/${id}/set-tier`,
      { method: "POST", body: { account_tier, reason } }
    ),
  revokeAccount: (id: string) =>
    apiFetch<{ status: string }>(`/gmail/accounts/${id}/revoke`, {
      method: "POST",
    }),
  purgeMockAccounts: () =>
    apiFetch<{ status: string }>("/gmail/accounts/mock", { method: "DELETE" }),
  syncReplies: (id: string) =>
    apiFetch<{
      new_replies: number;
      messages_scanned: number;
      reason: string;
    }>(`/gmail/accounts/${id}/sync-replies`, {
      method: "POST",
    }),
  mockConnect: (state: string) =>
    apiFetch<{ id: string; email: string; status: string }>(
      "/gmail/mock-connect",
      { method: "POST", params: { state } }
    ),
  connectInfo: () =>
    apiFetch<{
      use_mock_gmail: boolean;
      oauth_publishing_status: string;
      redirect_uri: string;
      redirect_uris_for_google_console: string[];
      google_client_id: string;
      google_client_configured: boolean;
      google_client_edit_url: string;
    }>("/gmail/connect-info"),
};

// Account pools
export const poolsApi = {
  list: async (params?: { page?: number; limit?: number }) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<import("@/types/api").AccountPool>
    >("/gmail/account-pools", { params }),
  get: (id: string) =>
    apiFetch<import("@/types/api").AccountPoolDetail>(
      `/gmail/account-pools/${id}`
    ),
  create: (data: Partial<import("@/types/api").AccountPool>) =>
    apiFetch<import("@/types/api").AccountPool>("/gmail/account-pools", {
      method: "POST",
      body: data,
    }),
  update: (id: string, data: Partial<import("@/types/api").AccountPool>) =>
    apiFetch<import("@/types/api").AccountPool>(`/gmail/account-pools/${id}`, {
      method: "PATCH",
      body: data,
    }),
  addMember: (
    poolId: string,
    data: { gmail_account_id: string; priority?: number; is_active?: boolean }
  ) =>
    apiFetch<import("@/types/api").AccountPoolMember>(
      `/gmail/account-pools/${poolId}/members`,
      { method: "POST", body: data }
    ),
  removeMember: (poolId: string, accountId: string) =>
    apiFetch<void>(`/gmail/account-pools/${poolId}/members/${accountId}`, {
      method: "DELETE",
    }),
};

// Risk
export const riskApi = {
  overview: () =>
    apiFetch<import("@/types/api").RiskOverview>("/risk/overview"),
  events: (params?: {
    from?: string;
    to?: string;
    event_type?: string;
    page?: number;
  }) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<import("@/types/api").RiskEvent>
    >("/risk/events", { params }),
  acknowledge: (data: {
    event_ids?: string[];
    acknowledge_all?: boolean;
    notes?: string;
  }) =>
    apiFetch<{ status: string }>("/risk/acknowledge", {
      method: "POST",
      body: data,
    }),
};

// Campaigns
export const campaignsApi = {
  list: (params?: {
    status?: string;
    page?: number;
    limit?: number;
  }) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<import("@/types/api").Campaign>
    >("/campaigns", { params }),
  get: (id: string) =>
    apiFetch<import("@/types/api").Campaign>(`/campaigns/${id}`),
  create: (data: {
    name: string;
    campaign_account_pool_id: string;
    template_id?: string;
    scheduled_start_at?: string;
    timezone?: string;
    send_window_start_hour?: number;
    send_window_end_hour?: number;
  }) =>
    apiFetch<import("@/types/api").Campaign>("/campaigns", {
      method: "POST",
      body: data,
    }),
  update: (id: string, data: Partial<import("@/types/api").Campaign>) =>
    apiFetch<import("@/types/api").Campaign>(`/campaigns/${id}`, {
      method: "PATCH",
      body: data,
    }),
  delete: (id: string) =>
    apiFetch<void>(`/campaigns/${id}`, { method: "DELETE" }),
  start: (id: string) =>
    apiFetch<{ status: string }>(`/campaigns/${id}/start`, {
      method: "POST",
    }),
  pause: (id: string) =>
    apiFetch<import("@/types/api").Campaign>(`/campaigns/${id}/pause`, {
      method: "POST",
    }),
  resume: (id: string) =>
    apiFetch<import("@/types/api").Campaign>(`/campaigns/${id}/resume`, {
      method: "POST",
    }),
  preflightCheck: (id: string) =>
    apiFetch<import("@/types/api").PreflightCheck>(
      `/campaigns/${id}/preflight-check`,
      { method: "POST" }
    ),
  listLeads: (
    id: string,
    params?: { status?: string; page?: number; limit?: number; search?: string }
  ) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<import("@/types/api").Lead>
    >(`/campaigns/${id}/leads`, { params }),
  createLead: (
    id: string,
    data: {
      email: string;
      first_name?: string;
      last_name?: string;
      company?: string;
      source?: string;
      compliance_acknowledged: boolean;
      allow_role_based_emails?: boolean;
    }
  ) =>
    apiFetch<import("@/types/api").Lead>(`/campaigns/${id}/leads`, {
      method: "POST",
      body: data,
    }),
  importLeads: (id: string, formData: FormData) =>
    apiFetch<import("@/types/api").LeadImportResponse>(
      `/campaigns/${id}/leads/import`,
      { method: "POST", body: formData }
    ),
  importStatus: (campaignId: string, jobId: string) =>
    apiFetch<import("@/types/api").LeadImportStatus>(
      `/campaigns/${campaignId}/leads/import/${jobId}`
    ),
  deleteLead: (campaignId: string, leadId: string) =>
    apiFetch<void>(`/campaigns/${campaignId}/leads/${leadId}`, {
      method: "DELETE",
    }),
  sendJobs: (
    id: string,
    params?: { status?: string; page?: number; limit?: number }
  ) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<import("@/types/api").SendJob>
    >(`/campaigns/${id}/send-jobs`, { params }),
  processQueue: (id: string) =>
    apiFetch<{
      jobs_created: number;
      jobs_processed: number;
      outcomes: Record<string, number>;
    }>(`/campaigns/${id}/process-queue`, { method: "POST" }),
};

// Templates
export const templatesApi = {
  list: (params?: { page?: number; limit?: number }) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<import("@/types/api").Template>
    >("/templates", { params }),
  get: (id: string) =>
    apiFetch<import("@/types/api").Template>(`/templates/${id}`),
  create: (data: {
    name: string;
    html_template: string;
    text_template?: string;
    subject_template?: string;
  }) =>
    apiFetch<import("@/types/api").Template>("/templates", {
      method: "POST",
      body: data,
    }),
  update: (id: string, data: Partial<import("@/types/api").Template>) =>
    apiFetch<import("@/types/api").Template>(`/templates/${id}`, {
      method: "PATCH",
      body: data,
    }),
  delete: (id: string) =>
    apiFetch<void>(`/templates/${id}`, { method: "DELETE" }),
  deleteAll: () =>
    apiFetch<{ deleted: number }>("/templates/delete-all", { method: "POST" }),
  preview: (
    id: string,
    lead_sample: Record<string, string>
  ) =>
    apiFetch<import("@/types/api").TemplatePreview>(
      `/templates/${id}/preview`,
      { method: "POST", body: { lead_sample } }
    ),
  importText: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<import("@/types/api").TextImportResult>(
      "/templates/import-text",
      { method: "POST", body: formData }
    );
  },
};

// Subject lines
export const subjectsApi = {
  list: () =>
    apiFetch<
      import("@/types/api").PaginatedResponse<import("@/types/api").EmailSubject>
    >("/subjects"),
  create: (data: { text: string }) =>
    apiFetch<import("@/types/api").EmailSubject>("/subjects", {
      method: "POST",
      body: data,
    }),
  delete: (id: string) =>
    apiFetch<void>(`/subjects/${id}`, { method: "DELETE" }),
  deleteAll: () =>
    apiFetch<{ deleted: number }>("/subjects/delete-all", { method: "POST" }),
  importText: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<import("@/types/api").TextImportResult>(
      "/subjects/import-text",
      { method: "POST", body: formData }
    );
  },
};

// Send timing settings
export const settingsApi = {
  getSendTiming: () =>
    apiFetch<import("@/types/api").SendTimingSettings>("/settings/send-timing"),
  updateSendTiming: (data: {
    account_cooldown_minutes?: number;
    inter_account_delay_min_minutes?: number;
    inter_account_delay_max_minutes?: number;
  }) =>
    apiFetch<import("@/types/api").SendTimingSettings>("/settings/send-timing", {
      method: "PATCH",
      body: data,
    }),
};

// Queue
export const queueApi = {
  stats: () => apiFetch<import("@/types/api").QueueStats>("/queue/stats"),
  accountTimeline: () =>
    apiFetch<import("@/types/api").AccountSendTimeline>("/queue/account-timeline"),
  resetSendHistory: () =>
    apiFetch<{
      campaigns_reset: number;
      campaigns_paused: number;
      redis_keys_cleared: number;
      reason: string;
    }>("/queue/reset-send-history", { method: "POST" }),
};

// Replies
export const repliesApi = {
  list: (params?: { campaign_id?: string; page?: number }) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<import("@/types/api").Reply>
    >("/replies", { params }),
};

// Unsubscribes
export const unsubscribesApi = {
  list: (params?: { page?: number }) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<
        import("@/types/api").UnsubscribeEntry
      >
    >("/unsubscribes", { params }),
  addManual: (email: string) =>
    apiFetch<import("@/types/api").UnsubscribeEntry>("/unsubscribes/manual", {
      method: "POST",
      body: { email },
    }),
  remove: (id: string) =>
    apiFetch<void>(`/unsubscribes/${id}`, { method: "DELETE" }),
};

// Analytics
export const analyticsApi = {
  overview: (params?: { from?: string; to?: string }) =>
    apiFetch<import("@/types/api").AnalyticsOverview>("/analytics/overview", {
      params,
    }),
  campaign: (id: string) =>
    apiFetch<import("@/types/api").CampaignAnalytics>(
      `/analytics/campaigns/${id}`
    ),
};

// Health
export const healthApi = {
  accounts: () =>
    apiFetch<{ items: import("@/types/api").HealthAccount[] }>(
      "/health/accounts"
    ),
  events: (id: string) =>
    apiFetch<{ items: import("@/types/api").HealthEvent[] }>(
      `/health/accounts/${id}/events`
    ),
};

// Audit logs
export const auditApi = {
  list: (params?: {
    action?: string;
    resource_type?: string;
    from?: string;
    to?: string;
    page?: number;
  }) =>
    apiFetch<
      import("@/types/api").PaginatedResponse<
        import("@/types/api").AuditLogEntry
      >
    >("/audit-logs", { params }),
};
