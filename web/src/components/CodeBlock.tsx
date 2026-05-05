"use client";

import { useState } from "react";
import clsx from "clsx";

type Props = {
  code: string;
  lang?: string;
  filename?: string;
  className?: string;
};

export default function CodeBlock({ code, lang, filename, className }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  return (
    <div
      className={clsx(
        "relative group rounded-lg overflow-hidden border border-border bg-zinc-950/80",
        className,
      )}
    >
      {(filename || lang) && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-zinc-900/60 text-xs text-text-soft">
          <span className="font-mono">{filename ?? lang}</span>
          <button
            onClick={copy}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-text-soft hover:text-accent"
          >
            {copied ? "✓ copied" : "copy"}
          </button>
        </div>
      )}
      <pre className="p-4 overflow-x-auto text-[13px] leading-relaxed">
        <code className="font-mono text-zinc-200 whitespace-pre">{code}</code>
      </pre>
    </div>
  );
}
