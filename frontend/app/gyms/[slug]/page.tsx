import { GymDetailPage } from "@/features/gyms/GymDetailPage";

export default function GymDetailRoute({ params }: { params: { slug: string } }) {
  return <GymDetailPage slug={params.slug} />;
}
