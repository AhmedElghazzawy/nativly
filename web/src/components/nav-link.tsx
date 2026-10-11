"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, type ReactNode } from "react";

type Props = { href: string; children: ReactNode; also?: string[] };

/** The highlight depends on the URL, so it streams in; the plain link renders immediately. */
export function NavLink(props: Props) {
  return (
    <Suspense fallback={<Item {...props} active={false} />}>
      <ActiveNavLink {...props} />
    </Suspense>
  );
}

function ActiveNavLink(props: Props) {
  const pathname = usePathname();
  const active = [props.href, ...(props.also ?? [])].some((p) => pathname.startsWith(p));
  return <Item {...props} active={active} />;
}

function Item({ href, children, active }: Props & { active: boolean }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`rounded-lg px-3 py-1.5 font-medium transition ${
        active ? "bg-accent-soft text-accent-strong" : "text-muted hover:text-ink"
      }`}
    >
      {children}
    </Link>
  );
}
