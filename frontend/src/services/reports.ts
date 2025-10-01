import { apiRequest } from "@/lib/apiClient";
import { encodeOnce } from "@/lib/url";

export type ReportGymIssueReason = "hours" | "equipment" | "address" | "closed" | "other";

export interface ReportGymIssuePayload {
  reason: ReportGymIssueReason;
  details: string;
  contact?: string;
}

export interface ReportGymIssueResponse {
  id?: number;
  status?: string;
}

export const reportGymIssue = async (
  slug: string,
  payload: ReportGymIssuePayload,
): Promise<ReportGymIssueResponse | undefined> =>
  apiRequest<ReportGymIssueResponse | undefined>(`/gyms/${encodeOnce(slug)}/report`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
