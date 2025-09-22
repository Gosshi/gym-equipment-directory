import { GymDetailPage } from "./GymDetailPage";

export default function GymDetailRoute({ params }: { params: { slug: string } }) {
  return <GymDetailPage slug={params.slug} />;
}
