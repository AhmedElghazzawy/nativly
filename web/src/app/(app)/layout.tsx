import { logout } from "@/app/(auth)/actions";
import { NavLink } from "@/components/nav-link";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <nav className="border-b border-line/70 bg-card/60">
        <div className="mx-auto flex h-12 w-full max-w-5xl items-center gap-1 px-4 text-sm">
          <NavLink href="/learn" also={["/lessons"]}>
            Learn
          </NavLink>
          <NavLink href="/progress">Progress</NavLink>
          <form action={logout} className="ml-auto">
            <button type="submit" className="rounded-lg px-3 py-1.5 text-muted hover:text-ink">
              Log out
            </button>
          </form>
        </div>
      </nav>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">{children}</main>
    </>
  );
}
