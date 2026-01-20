import { redirect } from "next/navigation";
import { auth } from "@/app/auth";
import SideMenu from "@/components/layout/side-menu";

export default async function CalendarLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  if (!session) {
    redirect("/auth/login");
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <SideMenu user={session.user} />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
