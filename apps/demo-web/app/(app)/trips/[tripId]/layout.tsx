import { TripShell } from "@/components/shell";

// The static AWS build prerenders one placeholder trip ("_"); CloudFront rewrites every real
// trip id to it and the pages read the real id from the address bar (useTripId).
export function generateStaticParams() {
  return [{ tripId: "_" }];
}

export default function TripLayout({ children }: { children: React.ReactNode }) {
  return <TripShell>{children}</TripShell>;
}
