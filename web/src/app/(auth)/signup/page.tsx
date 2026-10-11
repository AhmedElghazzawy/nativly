import type { Metadata } from "next";

import { signup } from "../actions";
import { AuthCard } from "../auth-card";
import { AuthForm } from "../auth-form";

export const metadata: Metadata = { title: "Create your account" };

export default function SignupPage() {
  return (
    <AuthCard title="Start learning" subtitle="Free, and it takes ten seconds.">
      <AuthForm action={signup} mode="signup" />
    </AuthCard>
  );
}
