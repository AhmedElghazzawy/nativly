import type { ReactNode } from "react";

export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-4 py-12">
      <h1 className="font-display text-3xl text-ink">{title}</h1>
      <p className="mt-2 mb-8 text-muted">{subtitle}</p>
      {children}
    </main>
  );
}
