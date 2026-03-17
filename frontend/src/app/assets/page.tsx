"use client";
import { useQuery } from "@tanstack/react-query";
import { macroIntelApi } from "@/lib/api";
import { BiasCard } from "@/components/shared/BiasCard";
import { TrendingUp } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

const CLASS_LABELS: Record<string, string> = {
  forex: "💱 Forex",
  equity_index: "📈 Indices",
  commodity: "🥇 Commodities",
  bond: "🏦 Bonds",
};

function AssetsContent() {
  const searchParams = useSearchParams();
  const [activeClass, setActiveClass] = useState<string>(searchParams.get("class") ?? "forex");

  const { data, isLoading } = useQuery({
    queryKey: ["bias-signals", activeClass],
    queryFn: () => macroIntelApi.getAllBiasSignals(activeClass),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <TrendingUp className="w-5 h-5 text-muted-foreground" />
        <h1 className="text-xl font-bold">Asset Analysis</h1>
      </div>

      <div className="flex gap-2">
        {Object.entries(CLASS_LABELS).map(([cls, label]) => (
          <button
            key={cls}
            onClick={() => setActiveClass(cls)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              activeClass === cls
                ? "bg-primary/10 border-primary/20 text-primary"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 animate-pulse">
          {[1,2,3,4,5,6,7,8].map(i => (
            <div key={i} className="h-48 bg-card border border-border rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {(data as any[] ?? []).map((signal: any) => (
            <BiasCard key={signal.symbol} signal={signal} />
          ))}
          {(!data || (data as any[]).length === 0) && (
            <div className="col-span-full card-base text-center py-8 text-muted-foreground text-sm">
              No bias signals available for this asset class.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AssetsPage() {
  return (
    <Suspense fallback={<div className="animate-pulse h-64 bg-card rounded-xl border border-border" />}>
      <AssetsContent />
    </Suspense>
  );
}
