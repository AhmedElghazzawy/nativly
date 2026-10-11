"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useActionState } from "react";

import type { AuthState } from "./actions";

type Props = {
  action: (state: AuthState, formData: FormData) => Promise<AuthState>;
  mode: "login" | "signup";
};

/** Where to go after logging in. Only this hidden field depends on the URL, so the visible
 * form renders immediately and never gets swapped out while someone is typing. */
function NextField() {
  const next = useSearchParams().get("next");
  return next ? <input type="hidden" name="next" value={next} /> : null;
}

export function AuthForm({ action, mode }: Props) {
  const [state, formAction, pending] = useActionState(action, {});
  const isLogin = mode === "login";

  return (
    <form action={formAction} className="space-y-5">
      <Suspense fallback={null}>
        <NextField />
      </Suspense>
      <label className="block">
        <span className="text-sm font-medium text-ink">Email</span>
        <input
          name="email"
          type="email"
          required
          autoComplete="email"
          defaultValue={state.email}
          className="field mt-1.5"
        />
      </label>
      <label className="block">
        <span className="text-sm font-medium text-ink">Password</span>
        <input
          name="password"
          type="password"
          required
          minLength={isLogin ? undefined : 8}
          autoComplete={isLogin ? "current-password" : "new-password"}
          className="field mt-1.5"
        />
        {!isLogin ? (
          <span className="mt-1 block text-xs text-muted">At least 8 characters.</span>
        ) : null}
      </label>

      {state.error ? (
        <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
          {state.error}
        </p>
      ) : null}

      <button type="submit" disabled={pending} className="btn-primary w-full">
        {pending ? "One moment…" : isLogin ? "Log in" : "Create account"}
      </button>

      <p className="text-center text-sm text-muted">
        {isLogin ? "New to Nativly? " : "Already have an account? "}
        <Link href={isLogin ? "/signup" : "/login"} className="font-medium text-accent underline">
          {isLogin ? "Create an account" : "Log in"}
        </Link>
      </p>
    </form>
  );
}
