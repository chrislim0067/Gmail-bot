// API response types for Gmail Cold-Email Outreach Platform

export type AccountTier =
  | "new"
  | "warming"
  | "stable"
  | "trusted"
  | "restricted"
  | "paused";

export type RiskLevel = "low" | "medium" | "high";

export type AccountStatus =
  | "active"
  | "paused"
  | "auth_error"
  | "revoked";

export type CampaignStatus =
  | "draft"
  | "scheduled"
  | "running"
  | "paused"
  | "completed"
  | "cancelled";

export type LeadStatus =
  | "pending"
  | "queued"
  | "sent"
  | "replied"
  | "bounced"
  | "unsubscribed"
  | "skipped"
  | "failed";

export type SendJobStatus =
  | "pending"
  | "locked"
  | "sent"
  | "failed"
  | "cancelled"
  | "skipped";

export interface ApiError {
  detail: string;
  code?: string;
  errors?: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages?: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  timezone?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface GmailAccount {
  id: string;
  email: string;
  status: AccountStatus;
  account_tier: AccountTier;
  risk_level: RiskLevel;
  review_required: boolean;
  health_score: number;
  tier_daily_default: number;
  tier_daily_hard_max: number;
  daily_send_limit: number;
  hourly_send_limit: number;
  connected_at: string;
  consecutive_success_days: number;
  bounce_rate_7d: number;
  error_rate_7d: number;
  recent_quota_errors: number;
  recent_auth_errors: number;
  last_send_at: string | null;
  sent_today: number;
  sent_this_hour: number;
  effective_daily_send_limit?: number;
  effective_hourly_send_limit?: number;
  remaining_today?: number;
  granted_scopes: string[];
}

export interface GmailAccountDetail extends GmailAccount {
  health_events?: HealthEvent[];
}

export interface AccountPool {
  id: string;
  name: string;
  description?: string;
  status?: string;
  max_daily_send?: number;
  max_hourly_send?: number;
  active_account_limit?: number;
  member_count?: number;
  sends_today?: number;
  sends_this_hour?: number;
  capacity_remaining?: number;
  created_at?: string;
}

export interface AccountPoolMember {
  id: string;
  gmail_account_id: string;
  email?: string;
  priority: number;
  is_active: boolean;
}

export interface AccountPoolDetail extends AccountPool {
  members: AccountPoolMember[];
}

export interface RiskOverview {
  global_risk_score: number;
  threshold: number;
  review_required: boolean;
  recent_events_count: number;
  paused_campaigns: number;
}

export interface RiskEvent {
  id: string;
  event_type: string;
  severity: string;
  score_delta: number;
  message: string;
  created_at: string;
  acknowledged?: boolean;
}

export interface Campaign {
  id: string;
  name: string;
  status: CampaignStatus;
  template_id?: string | null;
  campaign_account_pool_id: string;
  scheduled_start_at?: string | null;
  scheduled_end_at?: string | null;
  timezone?: string;
  send_window_start_hour?: number;
  send_window_end_hour?: number;
  preflight_passed_at?: string | null;
  total_leads?: number;
  sent_count?: number;
  replied_count?: number;
  bounced_count?: number;
  created_at?: string;
  updated_at?: string;
  stats?: CampaignStats;
}

export interface CampaignStats {
  total_leads: number;
  pending: number;
  queued: number;
  sent: number;
  replied: number;
  bounced: number;
  unsubscribed: number;
  failed: number;
  skipped: number;
}

export interface PreflightCheck {
  passed: boolean;
  checks: PreflightCheckItem[];
}

export interface PreflightCheckItem {
  name: string;
  passed: boolean;
  message: string;
}

export interface Lead {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  company?: string;
  status: LeadStatus;
  source?: string;
  source_url?: string;
  consent_basis?: string;
  import_batch_id?: string;
  created_at?: string;
}

export interface LeadImportResponse {
  import_batch_id: string;
  status: string;
  imported: number;
  skipped: number;
  invalid: number;
  errors: string[];
  job_id?: string;
}

export interface LeadImportStatus {
  status: string;
  imported: number;
  skipped: number;
  invalid?: number;
  errors: string[];
}

export interface Template {
  id: string;
  name: string;
  subject_template?: string | null;
  html_template: string;
  text_template?: string;
  created_at?: string;
  updated_at?: string;
}

export interface EmailSubject {
  id: string;
  text: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TextImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

export interface TemplatePreview {
  subject: string;
  html: string;
  text?: string;
}

export interface SendJob {
  id: string;
  campaign_id: string;
  lead_id: string;
  gmail_account_id?: string;
  status: SendJobStatus;
  scheduled_at?: string;
  sent_at?: string;
  error_message?: string;
  lead_email?: string;
  lead_name?: string;
  subject?: string;
}

export interface QueueStats {
  pending: number;
  locked: number;
  failed: number;
  sent_today: number;
}

export interface TimelineConstraint {
  reason: string;
  available_at?: string | null;
  retry_after_seconds: number;
  cooldown_total_seconds?: number;
}

export interface AccountSendTimelineEntry {
  gmail_account_id: string;
  email: string;
  account_status: string;
  last_send_at?: string | null;
  sent_today: number;
  available_now: boolean;
  retry_after_seconds: number;
  available_at?: string | null;
  inter_send_available_at?: string | null;
  reason?: string | null;
  inter_send_delay_seconds: number;
  inter_account_delay_min_seconds?: number;
  inter_account_delay_max_seconds?: number;
  queue_position?: number | null;
  cooldown_total_seconds?: number;
  constraints?: TimelineConstraint[];
  sent_this_hour?: number;
  hourly_cap?: number;
  daily_cap?: number;
}

export interface AccountSendTimeline {
  inter_send_delay_seconds: number;
  account_cooldown_seconds?: number;
  account_cooldown_minutes?: number;
  inter_account_delay_min_seconds?: number;
  inter_account_delay_max_seconds?: number;
  inter_account_delay_min_minutes?: number;
  inter_account_delay_max_minutes?: number;
  scheduler_tick_interval_seconds?: number;
  accounts: AccountSendTimelineEntry[];
}

export interface SendTimingSettings {
  account_cooldown_seconds: number;
  account_cooldown_minutes: number;
  inter_account_delay_min_seconds: number;
  inter_account_delay_max_seconds: number;
  inter_account_delay_min_minutes: number;
  inter_account_delay_max_minutes: number;
  scheduler_tick_interval_seconds: number;
}

export interface Reply {
  id: string;
  campaign_id?: string;
  campaign_name?: string;
  lead_id?: string;
  lead_email?: string;
  from_email?: string;
  subject?: string;
  snippet?: string;
  received_at: string;
  gmail_account_id?: string;
}

export interface UnsubscribeEntry {
  id: string;
  email: string;
  source: string;
  campaign_id?: string | null;
  unsubscribed_at?: string;
  created_at?: string;
}

export interface AnalyticsOverview {
  sent: number;
  replied: number;
  bounced: number;
  unsubscribed: number;
  reply_rate: number;
  bounce_rate: number;
}

export interface CampaignAnalytics {
  funnel: Record<string, number>;
  daily_breakdown: Array<{ date: string; sent: number; replied: number; bounced: number }>;
  account_breakdown: Array<{ account_id: string; email: string; sent: number }>;
}

export interface HealthAccount {
  id: string;
  email: string;
  health_score: number;
  account_tier: AccountTier;
  risk_level: RiskLevel;
  status: AccountStatus;
  bounce_rate_7d: number;
  error_rate_7d: number;
  alerts?: string[];
}

export interface HealthEvent {
  id: string;
  event_type: string;
  severity: string;
  message: string;
  score_delta?: number;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  user_id?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}
