import { apiRequest } from "@/lib/apiClient";
import type { ReportGymRequest, ReportGymResponse } from "@/types/api";

export const reportGym = async (
  slug: string,
  payload: ReportGymRequest,
): Promise<ReportGymResponse> =>
  apiRequest<ReportGymResponse>(`/gyms/${encodeURIComponent(slug)}/report`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
