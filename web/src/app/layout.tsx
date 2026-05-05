import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CostDNA — Ask your AWS bill questions in English",
  description:
    "A natural-language agent for AWS cost attribution. Combines a behavioral GraphSAGE GNN with LLM-derived semantic features and structured CloudTrail/Cost Explorer queries. Answers questions like 'why did our bill spike Tuesday?' with specific resources, teams, and dollar amounts.",
  metadataBase: new URL("https://pauti04.github.io/CostDNA"),
  openGraph: {
    title: "CostDNA — Ask your AWS bill questions in English",
    description:
      "Natural-language AWS cost attribution agent. Built on a behavioral GNN + LLM-augmented semantic features. Open source.",
    images: ["/images/umap-synthetic.png"],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "CostDNA — Ask your AWS bill questions in English",
    description: "Natural-language AWS cost attribution agent. Open source.",
    images: ["/images/umap-synthetic.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} dark`}>
      <body className="bg-zinc-950 text-zinc-100 antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
