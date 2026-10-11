import type { Metadata } from "next";
import { Suspense } from "react";

import { login } from "../actions";
import { AuthCard } from "../auth-card";
import { AuthForm } from "../auth-form";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage({ searchParams }: PageProps<"/login">) {
  return (
    <AuthCard title="Welcome back" subtitle="Pick up where you left off.">
      <Suspense fallback={<AuthForm action={login} mode="login" />}>
        <LoginForm searchParams={searchParams} />
      </Suspense>
    </AuthCard>
  );
}

async function LoginForm({ searchParams }: Pick<PageProps<"/login">, "searchParams">) {
  const { next } = await searchParams;
  return <AuthForm action={login} mode="login" next={typeof next === "string" ? next : undefined} />;
}
