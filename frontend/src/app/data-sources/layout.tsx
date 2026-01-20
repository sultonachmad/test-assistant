import SideMenu from "@/components/layout/side-menu";

export default function DataSourcesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen bg-gray-50">
      <SideMenu />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
