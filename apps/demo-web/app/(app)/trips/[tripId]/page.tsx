import Link from "next/link";

export default async function TripIndex({ params }: { params: Promise<{ tripId: string }> }) {
  const { tripId } = await params;
  const href = `/trips/${tripId}/itinerary/`;
  return (
    <>
      <meta httpEquiv="refresh" content={`0; url=${href}`} />
      <p className="py-10 text-center text-muted">Opening itinerary… <Link href={href} className="text-coral">Continue</Link></p>
    </>
  );
}
