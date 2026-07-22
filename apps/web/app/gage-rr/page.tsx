import { GageRRWorkspace } from "@/components/gage-rr-workspace";
import { PrintButton } from "@/components/print-button";

export default function GageRRPage() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-16">
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-semibold tracking-tight">Gage R&R</h1>
          <PrintButton />
        </div>
        <p className="text-foreground/70">
          How much of the variation you measure is the gage, not the parts?
          Enter a balanced study — each part measured by every operator, several
          times — and capstat partitions the variance into repeatability,
          reproducibility, and the real part-to-part spread. The grid is
          pre-filled with the AIAG worked example.
        </p>
      </header>
      <GageRRWorkspace />
    </main>
  );
}
