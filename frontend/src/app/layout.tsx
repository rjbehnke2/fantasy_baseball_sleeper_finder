import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fantasy Baseball Sleeper Finder",
  description: "AI-powered dynasty auction fantasy baseball analysis",
};

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/players", label: "Rankings" },
  { href: "/sleepers", label: "Sleepers" },
  { href: "/busts", label: "Busts" },
  { href: "/settings", label: "Settings" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex h-screen">
          {/* Sidebar */}
          <aside className="w-56 bg-gray-900 text-gray-100 flex flex-col shrink-0">
            <div className="px-4 py-5 border-b border-gray-700">
              <h1 className="text-lg font-bold tracking-tight">Sleeper Finder</h1>
              <p className="text-xs text-gray-400 mt-0.5">Dynasty Auction AI</p>
            </div>
            <nav className="flex-1 px-2 py-4 space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-800 hover:text-white transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-500">
              AI-Powered Analysis
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-y-auto">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
