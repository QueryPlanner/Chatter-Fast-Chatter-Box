import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import { PlayerProvider } from "@/components/providers/PlayerProvider";
import { GlobalPlayer } from "@/components/ui/GlobalPlayer";

export const metadata: Metadata = {
  title: "Chatterbox",
  description: "Chatterbox application",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col pb-32">
        <PlayerProvider>
          <header className="bg-surface border-b border-border-dark px-6 py-4">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              <Link href="/" className="text-xl font-bold text-primary">
                Chatterbox
              </Link>
              <nav className="flex gap-4">
                <Link href="/" className="text-text-main hover:text-primary">
                  Dashboard
                </Link>
                <Link href="/voices" className="text-text-main hover:text-primary">
                  Voices
                </Link>
              </nav>
            </div>
          </header>
          <main className="flex-1 max-w-7xl mx-auto w-full p-6">
            {children}
          </main>
          <GlobalPlayer />
        </PlayerProvider>
      </body>
    </html>
  );
}