import type { GymSummary } from "@/types/gym";

export interface Favorite {
  gym: GymSummary;
  createdAt: string | null;
}
