export default function Home() {
  return (
    <main className="mx-auto flex max-w-3xl flex-1 flex-col justify-center gap-6 px-6 py-16">
      <h1 className="text-4xl font-semibold tracking-tight">capstat</h1>
      <p className="text-lg text-foreground/70">
        Reference-validated statistical process control, process capability and
        measurement-system analysis — every result checked against published
        reference values.
      </p>
      <div className="rounded-lg border border-foreground/15 p-4 text-sm text-foreground/60">
        The interactive dashboard — file upload, capability report, and control
        charts — is under construction. The typed API client is wired to{" "}
        <code className="font-mono">capstat-api</code>.
      </div>
    </main>
  );
}
