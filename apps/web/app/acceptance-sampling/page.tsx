import { AcceptanceSamplingPanel } from "@/components/acceptance-sampling-panel";
import { PrintButton } from "@/components/print-button";

export default function AcceptanceSamplingPage() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-16">
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-semibold tracking-tight">
            Acceptance sampling
          </h1>
          <PrintButton />
        </div>
        <p className="text-foreground/70">
          Say which quality you are willing to accept and which you are not, and
          how much risk each side may carry, and capstat searches for the
          smallest plan that separates them — sample this many, reject on that
          many. The operating characteristic curve shows how steeply the plan
          falls between your two levels, which is the only honest way to compare
          plans. No standard&apos;s table is consulted: the plan is computed
          from your risks. It is pre-filled with a published worked example that
          designs to n = 144, Ac = 4.
        </p>
        <p className="text-foreground/70">
          Already have a plan — because a specification prescribes one, or a
          customer named an AQL scheme? Enter its sample size and acceptance
          number and press <strong>Judge this plan</strong>. capstat then
          reports what the table it came from does not: the risk each side
          actually carries at your two quality levels, the quality at which the
          plan is a coin flip, and how much inspection it costs.
        </p>
      </header>
      <AcceptanceSamplingPanel />
    </main>
  );
}
