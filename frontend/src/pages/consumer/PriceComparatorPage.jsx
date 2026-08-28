import { useState } from "react";

export default function PriceComparatorPage() {
  const [packA, setPackA] = useState({ name: "Standard Pack (A)", price: 45, qty: 500, unit: "g" });
  const [packB, setPackB] = useState({ name: "Family Pack (B)", price: 80, qty: 1000, unit: "g" });

  const getNormalizedPricePerKgOrL = (pack) => {
    const p = parseFloat(pack.price) || 0;
    const q = parseFloat(pack.qty) || 1;
    if (q <= 0) return 0;

    let qtyInStandardUnit = q;
    if (pack.unit === "g" || pack.unit === "ml") qtyInStandardUnit = q / 1000;
    return p / qtyInStandardUnit;
  };

  const costA = getNormalizedPricePerKgOrL(packA);
  const costB = getNormalizedPricePerKgOrL(packB);

  const diffPercent = costA > 0 ? Math.abs(((costA - costB) / costA) * 100).toFixed(1) : 0;
  const isBCheaper = costB < costA;
  const isEquivalent = Math.abs(costA - costB) < 0.01;

  return (
    <div className="space-y-6">
      <div className="card-slate bg-slate-900 text-white p-6 sm:p-8">
        <span className="text-[11px] font-bold px-2.5 py-1 rounded bg-sky-950 text-sky-400 border border-sky-800 uppercase tracking-wider">
          Legal Metrology Rule 6(1)(g) Utility
        </span>
        <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white mt-2">
          Unit Sale Price (USP) Comparator
        </h2>
        <p className="text-xs sm:text-sm text-slate-300 mt-2 max-w-3xl leading-relaxed">
          Compare the true cost per unit (per kg / litre) across different packaging sizes to uncover hidden shrinkflation and find the true cost-effective option.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pack A Card */}
        <div className="card-slate p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-black text-slate-900">Option A</h3>
            <span className="text-xs font-bold text-slate-500">First Pack</span>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Package Name / Size</label>
            <input
              type="text"
              value={packA.name}
              onChange={(e) => setPackA({ ...packA, name: e.target.value })}
              className="input-field text-xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Price (₹)</label>
              <input
                type="number"
                step="0.1"
                value={packA.price}
                onChange={(e) => setPackA({ ...packA, price: e.target.value })}
                className="input-field text-xs"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Quantity</label>
              <div className="flex gap-1">
                <input
                  type="number"
                  step="1"
                  value={packA.qty}
                  onChange={(e) => setPackA({ ...packA, qty: e.target.value })}
                  className="input-field text-xs flex-1"
                />
                <select
                  value={packA.unit}
                  onChange={(e) => setPackA({ ...packA, unit: e.target.value })}
                  className="input-field text-xs w-16"
                >
                  <option value="g">g</option>
                  <option value="kg">kg</option>
                  <option value="ml">ml</option>
                  <option value="L">L</option>
                </select>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Unit Price:</span>
            <p className="text-xl font-black text-slate-900 mt-0.5">
              ₹{costA.toFixed(2)} <span className="text-xs text-slate-500 font-medium">per {packA.unit === "ml" || packA.unit === "L" ? "L" : "kg"}</span>
            </p>
          </div>
        </div>

        {/* Pack B Card */}
        <div className="card-slate p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-black text-slate-900">Option B</h3>
            <span className="text-xs font-bold text-slate-500">Second Pack</span>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Package Name / Size</label>
            <input
              type="text"
              value={packB.name}
              onChange={(e) => setPackB({ ...packB, name: e.target.value })}
              className="input-field text-xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Price (₹)</label>
              <input
                type="number"
                step="0.1"
                value={packB.price}
                onChange={(e) => setPackB({ ...packB, price: e.target.value })}
                className="input-field text-xs"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Quantity</label>
              <div className="flex gap-1">
                <input
                  type="number"
                  step="1"
                  value={packB.qty}
                  onChange={(e) => setPackB({ ...packB, qty: e.target.value })}
                  className="input-field text-xs flex-1"
                />
                <select
                  value={packB.unit}
                  onChange={(e) => setPackB({ ...packB, unit: e.target.value })}
                  className="input-field text-xs w-16"
                >
                  <option value="g">g</option>
                  <option value="kg">kg</option>
                  <option value="ml">ml</option>
                  <option value="L">L</option>
                </select>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Unit Price:</span>
            <p className="text-xl font-black text-slate-900 mt-0.5">
              ₹{costB.toFixed(2)} <span className="text-xs text-slate-500 font-medium">per {packB.unit === "ml" || packB.unit === "L" ? "L" : "kg"}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Comparison Outcome Banner */}
      <div className={`p-6 rounded-2xl border text-center transition-all ${
        isEquivalent
          ? "bg-slate-100 border-slate-300 text-slate-800"
          : isBCheaper
          ? "bg-emerald-50 border-emerald-200 text-emerald-900"
          : "bg-sky-50 border-sky-200 text-sky-900"
      }`}>
        <span className="text-2xl">💡</span>
        <h4 className="text-base font-black mt-1">
          {isEquivalent
            ? "Both packages have equal price per unit quantity"
            : isBCheaper
            ? `${packB.name} is ${diffPercent}% cheaper per unit quantity`
            : `${packA.name} is ${diffPercent}% cheaper per unit quantity`}
        </h4>
        <p className="text-xs opacity-80 mt-1">
          Under Legal Metrology Rule 6(1)(g), every packaged commodity must declare its true Unit Sale Price so buyers can make direct comparisons.
        </p>
      </div>
    </div>
  );
}
