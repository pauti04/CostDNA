import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Analytics from "@/components/Analytics";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CostDNA — A 97% accuracy result. Audited. It was a tautology.",
  description:
    "Behavioral GNN for cloud-resource attribution. While evaluating on Microsoft's published 2.6M-VM Azure trace I caught label leakage that inflated first-cut accuracy from 6.9% to 97%. The honest negative result became the project's strongest finding.",
  metadataBase: new URL("https://cost-dna.vercel.app"),
  alternates: { canonical: "/" },
  openGraph: {
    title: "CostDNA — A 97% accuracy result. Audited. It was a tautology.",
    description:
      "Behavioral GNN for cloud-resource attribution. Methodology audit caught label leakage in two published Microsoft cloud datasets. Open source.",
    images: [
      {
        url: "/images/audit-hero.png",
        width: 2400,
        height: 1350,
        alt: "CostDNA audit chart — 97% first-cut accuracy became 6.9% honest after the deployment_id leak was excluded.",
      },
    ],
    type: "website",
    url: "https://cost-dna.vercel.app",
    siteName: "CostDNA",
  },
  twitter: {
    card: "summary_large_image",
    title: "CostDNA — A 97% accuracy result. Audited. It was a tautology.",
    description:
      "Caught label leakage in Microsoft's published 2.6M-VM Azure dataset. Open-source behavioral GNN + methodology audit.",
    images: ["/images/audit-hero.png"],
  },
  keywords: [
    "cloud-resource attribution",
    "methodology audit",
    "label leakage",
    "GraphSAGE",
    "Graph Neural Network",
    "PyTorch Geometric",
    "Microsoft Azure trace",
    "FinOps",
    "cost attribution",
    "node2vec",
    "machine learning research",
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
