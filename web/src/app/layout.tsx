import type { Metadata } from "next";
import { Fraunces, Geist } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const geist = Geist({ variable: "--font-geist-sans", subsets: ["latin", "latin-ext"] });
const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin", "latin-ext"] });

export const metadata: Metadata = {
  title: { default: "Nativly — Native gibi konuş", template: "%s · Nativly" },
  description:
    "An AI language school that teaches like a real teacher: a real curriculum, explanations that tell you why, and progress you can see.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geist.variable} ${fraunces.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col font-sans">
        <header className="border-b border-line/70">
          <div className="mx-auto flex h-16 w-full max-w-5xl items-center px-4">
            <Link href="/" className="font-display text-2xl font-semibold text-ink">
              Nativly<span className="text-accent">.</span>
            </Link>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
