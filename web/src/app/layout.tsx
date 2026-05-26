import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Analytics from "@/components/Analytics";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CostDNA — Attribute the 40–60% of your AWS bill that's untagged",
  description:
    "Open-source behavioural GNN that infers cloud-resource ownership from CloudTrail. Writes tags back so CloudHealth, Vantage, Datadog CCM, and Kubecost see 95% of spend instead of 50%. Self-hosted; no data leaves your account.",
  metadataBase: new URL("https://cost-dna.vercel.app"),
  alternates: { canonical: "/" },
  openGraph: {
    title: "CostDNA — Attribute the 40–60% of your AWS bill that's untagged",
    description:
      "Behavioural GNN infers ownership of untagged AWS resources. Writes tags back. Every FinOps tool you already pay for suddenly explains 95% of spend.",
    images: [
      {
        url: "/images/audit-hero.png",
        width: 2400,
        height: 1350,
        alt: "CostDNA — the 40-60% of your AWS bill that's untagged, attributed.",
      },
    ],
    type: "website",
    url: "https://cost-dna.vercel.app",
    siteName: "CostDNA",
  },
  twitter: {
    card: "summary_large_image",
    title: "CostDNA — Attribute the 40–60% of your AWS bill that's untagged",
    description:
      "Open-source behavioural GNN. Self-hosted, MIT, no data leaves your account. Methodology peer-validated on Microsoft Azure 2.6M-VM dataset.",
    images: ["/images/audit-hero.png"],
  },
  keywords: [
    "cloud cost attribution",
    "AWS cost allocation",
    "FinOps tooling",
    "inferred tags",
    "untagged AWS spend",
    "CloudTrail",
    "Graph Neural Network",
    "GraphSAGE",
    "cloud cost intelligence",
    "open-source FinOps",
    "Cost & Usage Report",
    "tag drift",
    "chargeback automation",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body className="bg-bg text-text antialiased font-sans">
        <Analytics />
        {children}
      </body>
    </html>
  );
}
