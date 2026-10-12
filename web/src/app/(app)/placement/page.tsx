import type { Metadata } from "next";
import { Suspense } from "react";

import { PlacementRunner } from "@/components/placement/placement-runner";
import { getLatestPlacement } from "@/lib/data";

export const metadata: Metadata = { title: "Placement test" };

export default function PlacementPage() {
  return (
    <Suspense
      fallback={<div className="mx-auto h-96 max-w-xl animate-pulse rounded-2xl bg-line/50" />}
    >
      <Placement />
    </Suspense>
  );
}

async function Placement() {
  return <PlacementRunner initial={await getLatestPlacement()} />;
}
