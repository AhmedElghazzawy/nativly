import Link from "next/link";

const PILLARS = [
  {
    title: "A real curriculum",
    body: "CEFR levels A1 to C2, built unit by unit around what you can actually do: talk about your past, make plans, explain your opinion.",
  },
  {
    title: "Explanations, not just answers",
    body: "Every exercise tells you why. Wrong answers come with the rule and an example, the way a good teacher corrects you.",
  },
  {
    title: "Progress you can see",
    body: "Nativly tracks how well you know each skill and shows your weakest areas first, so practice goes where it helps most.",
  },
];

export default function Home() {
  return (
    <main className="flex-1">
      <section className="mx-auto max-w-5xl px-4 pt-16 pb-20 sm:pt-24">
        <p className="mb-4 inline-block rounded-full bg-accent-soft px-3 py-1 text-sm font-medium text-accent-strong">
          English · A2 now open
        </p>
        <h1 className="max-w-3xl font-display text-5xl leading-[1.05] text-ink sm:text-6xl">
          Learn English with a teacher who explains <em className="text-accent">why</em>.
        </h1>
        <p className="mt-6 max-w-xl text-lg text-muted">
          Short lessons, real explanations and exercises that correct you like a person would.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/signup" className="btn-primary px-6">
            Start learning free
          </Link>
          <Link href="/login" className="btn-secondary px-6">
            I have an account
          </Link>
        </div>
      </section>

      <section className="border-t border-line/70 bg-card">
        <div className="mx-auto grid max-w-5xl gap-8 px-4 py-16 sm:grid-cols-3">
          {PILLARS.map((pillar) => (
            <div key={pillar.title}>
              <h2 className="font-display text-xl text-ink">{pillar.title}</h2>
              <p className="mt-2 leading-relaxed text-muted">{pillar.body}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
