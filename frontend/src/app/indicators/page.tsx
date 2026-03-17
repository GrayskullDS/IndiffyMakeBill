"use client";
import { useQuery } from "@tanstack/react-query";
import { macroIntelApi } from "@/lib/api";
import { useState } from "react";
import { BarChart3, Search } from "lucide-react";

const CATEGORY_LABELS: Record<string, string> = {
  growth: "Growth",
  inflation: "Inflation",
  labor: "Labor Market",
  monetary: "Monetary Policy",
  sentiment: "Sentiment",
  positioning: "Positioning",
  price: "Price",
  volatility: "Volatility",
};

export default function IndicatorsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [search, setSearch] = useState("");

  const { data: indicators = [] } = useQuery({
    queryKey: ["indicators", selectedCategory],
    queryFn: () => macroIntelApi.getIndicators(selectedCategory),
  });

  const { data: macroDash } = useQuery({
    queryKey: ["macro-dashboard"],
    queryFn: macroIntelApi.getMacroDashboard,
  });

  const categories = Object.keys(CATEGORY_LABELS);

  const filteredIndicators = (indicators as any[]).filter((i: any) =>
    !search || i.name.toLowerCase().includes(search.toLowerCase()) || i.code.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <BarChart3 className="w-5 h-5 text-muted-foreground" />
        <h1 className="text-xl font-bold">Macro Indicators</h1>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCategory(undefined)}
          className={`px-3 py-1 rounded-full text-xs border transition-colors ${
            !selectedCategory ? "bg-primary/10 border-primary/20 text-primary" : "border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1 rounded-full text-xs border transition-colors ${
              selectedCategory === cat ? "bg-primary/10 border-primary/20 text-primary" : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
        <div className="flex items-center gap-2 ml-auto">
          <Search className="w-3.5 h-3.5 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search indicators..."
            className="bg-card border border-border rounded-lg px-3 py-1 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 w-48"
          />
        </div>
      </div>

      {/* Dashboard snapshot */}
      {macroDash && (
        <div className="card-base">
          <h3 className="text-sm font-semibold mb-3">Latest Readings</h3>
          <div className="overflow-x-auto">
            <table className="w-full data-table">
              <thead>
                <tr>
                  <th>Indicator</th>
                  <th>Category</th>
                  <th>Value</th>
                  <th>Change</th>
                  <th>Date</th>
                  <th>Unit</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(macroDash as any).flatMap(([cat, rows]: any) =>
                  (rows as any[])
                    .filter((r: any) => !selectedCategory || r.category === selectedCategory)
                    .filter((r: any) => !search || r.name.toLowerCase().includes(search.toLowerCase()))
                    .map((r: any) => (
                      <tr key={r.code}>
                        <td>
                          <div className="font-medium text-foreground text-xs">{r.name}</div>
                          <div className="text-[10px] text-muted-foreground font-mono">{r.code}</div>
                        </td>
                        <td>
                          <span className="text-xs capitalize text-muted-foreground">{r.category}</span>
                        </td>
                        <td>
                          <span className="font-mono text-sm font-semibold">
                            {r.value !== null ? Number(r.value).toFixed(2) : "—"}
                          </span>
                        </td>
                        <td>
                          {r.change !== null ? (
                            <span className={`font-mono text-xs ${r.change > 0 ? "text-green-400" : "text-red-400"}`}>
                              {r.change > 0 ? "+" : ""}{r.change?.toFixed(3)}
                            </span>
                          ) : "—"}
                        </td>
                        <td>
                          <span className="text-xs text-muted-foreground font-mono">{r.date}</span>
                        </td>
                        <td>
                          <span className="text-xs text-muted-foreground">{r.unit ?? "—"}</span>
                        </td>
                      </tr>
                    ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
