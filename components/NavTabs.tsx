"use client";

import { useSearchParams, useParams } from "next/navigation";
import Link from "next/link";

export default function NavTabs() {
  const params = useParams();
  const searchParams = useSearchParams();
  const secret = params.secret as string;
  const filter = searchParams.get("filter");

  const tabs = [
    { label: "Каталог", href: `/catalog/${secret}`, active: !filter },
    { label: "★ Хит", href: `/catalog/${secret}?filter=hit`, active: filter === "hit" },
    { label: "✦ Новинка", href: `/catalog/${secret}?filter=new`, active: filter === "new" },
  ];

  return (
    <nav className="flex gap-1">
      {tabs.map((tab) => (
        <Link
          key={tab.label}
          href={tab.href}
          className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
            tab.active
              ? "bg-white text-blue-600"
              : "text-white/90 hover:bg-blue-500 active:bg-blue-500"
          }`}
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}
