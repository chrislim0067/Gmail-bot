import type { Campaign } from "@/types/api";

export function campaignEmailsSent(campaign: Campaign): number {
  return campaign.stats?.sent ?? campaign.sent_count ?? 0;
}

export function campaignReplies(campaign: Campaign): number {
  return campaign.stats?.replied ?? campaign.replied_count ?? 0;
}

export function campaignPeopleCount(campaign: Campaign): number {
  return campaign.stats?.total_leads ?? campaign.total_leads ?? 0;
}
