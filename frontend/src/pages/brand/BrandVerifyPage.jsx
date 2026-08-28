import ScanProductPage from "../consumer/ScanProductPage";

export default function BrandVerifyPage() {
  return (
    <div className="space-y-6">
      <div className="card-slate bg-slate-900 text-white p-6 sm:p-8">
        <span className="text-[11px] font-bold px-2.5 py-1 rounded bg-purple-950 text-purple-400 border border-purple-800 uppercase tracking-wider">
          Brand Pre-Market QA Engine
        </span>
        <h2 className="text-2xl font-black tracking-tight text-white mt-2">
          Verify SKU Artwork & Label Proofs
        </h2>
        <p className="text-xs sm:text-sm text-slate-300 mt-2 max-w-2xl leading-relaxed">
          Upload pre-print packaging artwork or physical sample photos. The AI engine audits all 8 mandatory Legal Metrology declarations before commercial dispatch.
        </p>
      </div>

      <ScanProductPage />
    </div>
  );
}
