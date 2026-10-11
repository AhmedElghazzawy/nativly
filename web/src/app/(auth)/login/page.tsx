import type { Metadata } from "next";

import { login } from "../actions";
import { AuthCard } from "../auth-card";
import { AuthForm } from "../auth-form";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  return (
    <AuthCard title="Welcome back" subtitle="Pick up where you left off.">
      <AuthForm action={login} mode="login" />
    </AuthCard>
  );
}
