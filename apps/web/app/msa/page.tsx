import { BiasPanel } from "@/components/bias-panel";
import { LinearityPanel } from "@/components/linearity-panel";
import { StabilityPanel } from "@/components/stability-panel";

export default function MsaPage() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">
          Bias, linearity, stability
        </h1>
        <p className="text-foreground/70">
          Gage R&amp;R asks whether a measurement system is <em>consistent</em>.
          These three ask whether it is <em>right</em> — and they need something
          Gage R&amp;R does not: a part whose true value you already know. Each
          study below is pre-filled with a worked example.
        </p>
      </header>
      <BiasPanel />
      <hr className="border-foreground/10" />
      <LinearityPanel />
      <hr className="border-foreground/10" />
      <StabilityPanel />
    </main>
  );
}
