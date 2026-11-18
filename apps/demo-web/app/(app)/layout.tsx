import { AppNav, Footer } from "@/components/ui";
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (<><AppNav />{children}<Footer /></>);
}
