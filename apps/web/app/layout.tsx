import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "capstat",
  description:
    "Reference-validated SPC, process capability and MSA — in the browser.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <nav className="flex items-center gap-5 border-b border-foreground/10 px-6 py-3 text-sm">
          <Link href="/" className="font-semibold tracking-tight">
            capstat
          </Link>
          <Link href="/" className="text-foreground/60 hover:text-foreground">
            Capability &amp; charts
          </Link>
          <Link
            href="/gage-rr"
            className="text-foreground/60 hover:text-foreground"
          >
            Gage R&amp;R
          </Link>
          <Link
            href="/msa"
            className="text-foreground/60 hover:text-foreground"
          >
            Bias &amp; linearity
          </Link>
          <Link
            href="/acceptance-sampling"
            className="text-foreground/60 hover:text-foreground"
          >
            Acceptance sampling
          </Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
