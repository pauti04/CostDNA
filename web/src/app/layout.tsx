import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Analytics from "@/components/Analytics";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CostDNA — Ask your AWS bill questions in English",
  description:
    "A natural-language agent for cloud cost attribution. Production-tested on AWS (87% per-resource accuracy on a real account), methodology validated on Microsoft's 2.6M-VM Azure trace. Multi-cloud architecture, open source.",
  metadataBase: new URL("https://cost-dna.vercel.app"),
  alternates: { canonical: "/" },
  openGraph: {
    title: "CostDNA — Ask your AWS bill questions in English",
    description:
      "Natural-language cloud-cost agent. 87% on real AWS, +53% lift over best baseline, multi-cloud architecture. Open source.",
    images: [
      {
        url: "/images/og-card.png",
        width: 1200,
        height: 630,
        alt: "CostDNA — Ask your AWS bill questions in English",
      },
    ],
    type: "website",
    url: "https://cost-dna.vercel.app",
    siteName: "CostDNA",
  },
  twitter: {
    card: "summary_large_image",
    title: "CostDNA — Ask your AWS bill questions in English",
    description: "Natural-language cloud-cost agent. 87% on real AWS. Open source.",
    images: ["/images/og-card.png"],
  },
  keywords: [
    "AWS cost attribution",
    "FinOps",
    "GraphSAGE",
    "Graph Neural Network",
    "CloudTrail",
    "cost allocation",
    "cloud tagging",
    "Cost Explorer",
    "natural language agent",
    "LLM",
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
