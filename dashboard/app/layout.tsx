import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniMed-Nexus",
  description: "God-mode ML orchestration hub — codesense-ai · MedFusion-Leuk · medbrain-ai",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gray-950 text-gray-100 font-mono antialiased">
        <nav className="border-b border-gray-800 px-6 py-4 flex items-center gap-4">
          <span className="text-emerald-400 font-bold text-lg tracking-tight">OmniMed-Nexus</span>
          <span className="text-gray-500 text-xs">god-mode orchestrator</span>
          <div className="ml-auto flex gap-6 text-sm text-gray-400">
            <a href="/" className="hover:text-white transition-colors">Dashboard</a>
            <a href="/findings" className="hover:text-white transition-colors">Findings</a>
            <a href="/models" className="hover:text-white transition-colors">Models</a>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
