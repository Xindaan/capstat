import { PrintButton } from "@/components/print-button";
import { Workspace } from "@/components/workspace";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-16">
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-4xl font-semibold tracking-tight">capstat</h1>
          <PrintButton />
        </div>
        <p className="text-lg text-foreground/70">
          Reference-validated statistical process control, process capability
          and measurement-system analysis — every result checked against
          published reference values.
        </p>
      </header>
      <Workspace />
    </main>
  );
}
