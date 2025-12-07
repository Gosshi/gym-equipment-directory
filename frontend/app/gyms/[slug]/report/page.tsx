import { notFound } from "next/navigation";

import { ApiError } from "@/lib/apiClient";
import { getGymBySlug } from "@/services/gyms";

import { ReportGymForm } from "./ReportGymForm";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function GymReportPage({ params }: PageProps) {
  const { slug } = await params;
  let gymName: string | undefined;

  try {
    const detail = await getGymBySlug(slug);
    gymName = detail.name;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
  }

  return <ReportGymForm slug={slug} gymName={gymName} />;
}
