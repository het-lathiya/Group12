import { TripHeader } from "@/components/ui";
import { trips } from "@/lib/data";

export const dynamicParams = false;
export function generateStaticParams() {
  return trips.map((t) => ({ tripId: t.id }));
}

export default async function TripLayout({ children, params }: { children: React.ReactNode; params: Promise<{ tripId: string }> }) {
  const { tripId } = await params;
  return (<><TripHeader tripId={tripId} /><div className="mx-auto max-w-[1440px] px-4 py-6 md:px-6">{children}</div></>);
}
