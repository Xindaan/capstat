import { MsaWorkspace } from "@/components/msa-workspace";
import { PrintButton } from "@/components/print-button";

export default function MsaPage() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-semibold tracking-tight">
            Bias, linearity, stability
          </h1>
          <PrintButton />
        </div>
        <p className="text-foreground/70">
          Gage R&amp;R asks whether a measurement system is <em>consistent</em>.
          These three ask whether it is <em>right</em> — and they need something
          Gage R&amp;R does not: a part whose true value you already know. Each
          study below is pre-filled with a worked example.
        </p>
      </header>
      <MsaWorkspace />
    </main>
  );
}
