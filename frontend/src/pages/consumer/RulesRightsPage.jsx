import { useState } from "react";
import AppDrawer from "../../components/AppDrawer";

const RULES_DATA = [
  {
    id: "manufacturer_name_address",
    name: "Manufacturer Name & Address",
    ruleNumber: "Rule 6(1)(a)",
    severity: "Critical",
    points: 15,
    summary: "Complete name and physical premises address of the manufacturer, packer, or importer.",
    whatChecks: "Checks for keywords such as 'Manufactured by', 'Packed at', 'Imported by' alongside valid physical address tokens.",
    whyItMatters: "Allows consumers and enforcement authorities to hold manufacturers accountable for product defects, recalls, or adulteration.",
    penalty: "Section 36 of Legal Metrology Act, 2009: Fine up to ₹25,000 for first offence, ₹50,000 for second.",
  },
  {
    id: "product_name",
    name: "Generic / Commodity Name",
    ruleNumber: "Rule 6(1)(b)",
    severity: "Critical",
    points: 15,
    summary: "Generic name or common commodity name of the pre-packaged product.",
    whatChecks: "Checks for clear generic title such as 'Iodised Salt', 'Wheat Flour', 'Shampoo' rather than misleading trade fantasy names alone.",
    whyItMatters: "Prevents deceptive branding from disguising the true nature of the commodity.",
    penalty: "Notice and seizure of non-compliant packaged lots under Rule 29.",
  },
  {
    id: "net_quantity",
    name: "Net Quantity Declaration",
    ruleNumber: "Rule 6(1)(c) & Rule 12",
    severity: "Critical",
    points: 15,
    summary: "Net weight, volume, or count in standard metric units (kg, g, l, ml, pcs).",
    whatChecks: "Validates standard metric units, font height tolerances based on package size, and maximum permissible error margins.",
    whyItMatters: "Ensures consumers get the exact weight or volume paid for, protecting against short-measure.",
    penalty: "Section 30 of Act: Fine up to ₹10,000 for short-weight/measure violations.",
  },
  {
    id: "manufacturing_date",
    name: "Date of Manufacture / Packaging",
    ruleNumber: "Rule 6(1)(d)",
    severity: "Critical",
    points: 15,
    summary: "Month and year of manufacture or pre-packaging (e.g. 08/2026).",
    whatChecks: "Detects numerical/month date patterns near 'Mfg Date', 'Packed on', 'Mfg:', 'Mfd:'.",
    whyItMatters: "Determines product freshness, shelf-life, and expiry timeline for consumer safety.",
    penalty: "Seizure of expired or undated goods.",
  },
  {
    id: "mrp",
    name: "Maximum Retail Price (MRP)",
    ruleNumber: "Rule 6(1)(e)",
    severity: "Critical",
    points: 15,
    summary: "Maximum retail price inclusive of all taxes (e.g. 'MRP Rs 45.00 incl. of all taxes').",
    whatChecks: "Detects MRP amounts, currency symbols (₹, Rs), and mandatory 'incl. of all taxes' statement.",
    whyItMatters: "Prevents overcharging above the declared price and mandates tax transparency.",
    penalty: "Selling above MRP attracts penalties up to ₹50,000 under Section 36(1).",
  },
  {
    id: "consumer_care_contact",
    name: "Consumer Grievance / Care Contact",
    ruleNumber: "Rule 6(1)(f)",
    severity: "Minor",
    points: 5,
    summary: "Toll-free telephone number, email, and address of the grievance redressal officer.",
    whatChecks: "Searches for phone patterns, helpline numbers (1800-...), or support email addresses.",
    whyItMatters: "Gives consumers a direct statutory avenue to lodge quality or billing complaints.",
    penalty: "Statutory notice for omission.",
  },
  {
    id: "unit_sale_price",
    name: "Unit Sale Price (USP)",
    ruleNumber: "Rule 6(1)(g)",
    severity: "Minor",
    points: 5,
    summary: "Price per unit measure (per kg, per gram, per litre, per piece).",
    whatChecks: "Checks for 'Rs ... / kg' or 'Rs ... / 100g' declarations on packages with net content > 1kg/1L.",
    whyItMatters: "Empowers consumers to directly compare true costs across different package sizes without mental arithmetic.",
    penalty: "Mandatory compliance enforcement for packaged commodities.",
  },
  {
    id: "country_of_origin",
    name: "Country of Origin",
    ruleNumber: "Rule 6(1)(h)",
    severity: "Critical",
    points: 15,
    summary: "Country of manufacture or country of origin for imported commodities.",
    whatChecks: "Detects 'Made in India', 'Country of Origin: ...', or importer origin tokens.",
    whyItMatters: "Informs consumers about origin and satisfies import declaration regulations.",
    penalty: "Customs and Legal Metrology joint confiscation for imported goods.",
  },
];

export default function RulesRightsPage() {
  const [selectedRule, setSelectedRule] = useState(null);

  return (
    <div className="space-y-6">
      <div className="card-slate bg-slate-900 text-white p-6 sm:p-8">
        <span className="text-[11px] font-bold px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase tracking-wider">
          Statutory Reference
        </span>
        <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white mt-2">
          Legal Metrology (Packaged Commodities) Rules, 2011
        </h2>
        <p className="text-xs sm:text-sm text-slate-300 mt-2 max-w-3xl leading-relaxed">
          Under Indian law, every pre-packaged commodity sold to consumers must carry <strong>8 mandatory declarations</strong>. LabelSetu’s optical engine evaluates packaging against these statutory requirements.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {RULES_DATA.map((rule) => (
          <div
            key={rule.id}
            onClick={() => setSelectedRule(rule)}
            className="card-slate-hover p-5 cursor-pointer flex flex-col justify-between group"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono font-bold text-slate-400">{rule.ruleNumber}</span>
                <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded ${
                  rule.severity === "Critical"
                    ? "bg-red-50 text-red-700 border border-red-200"
                    : "bg-amber-50 text-amber-700 border border-amber-200"
                }`}>
                  {rule.severity} ({rule.points} pts)
                </span>
              </div>
              <h3 className="text-sm font-extrabold text-slate-900 group-hover:text-emerald-700 transition-colors">
                {rule.name}
              </h3>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                {rule.summary}
              </p>
            </div>

            <div className="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-emerald-600">
              <span>View Rule Specs & Checks</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </div>
          </div>
        ))}
      </div>

      {/* Rule Detail Drawer */}
      <AppDrawer
        isOpen={Boolean(selectedRule)}
        onClose={() => setSelectedRule(null)}
        title={selectedRule?.name || "Rule Specification"}
        subtitle={selectedRule?.ruleNumber}
      >
        {selectedRule && (
          <div className="space-y-4">
            <div className="card-slate p-4 bg-slate-50/50">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Statutory Mandate</span>
              <p className="text-xs font-medium text-slate-800 mt-1 leading-relaxed">{selectedRule.summary}</p>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">What LabelSetu Checks</h4>
              <p className="text-xs text-slate-600 bg-white p-3 rounded-xl border border-slate-200 leading-relaxed">
                {selectedRule.whatChecks}
              </p>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Why It Matters for Consumers</h4>
              <p className="text-xs text-slate-600 bg-emerald-50/50 p-3 rounded-xl border border-emerald-200 leading-relaxed">
                {selectedRule.whyItMatters}
              </p>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Legal Enforcement Penalty</h4>
              <p className="text-xs text-slate-600 bg-red-50/50 p-3 rounded-xl border border-red-200 leading-relaxed">
                {selectedRule.penalty}
              </p>
            </div>
          </div>
        )}
      </AppDrawer>
    </div>
  );
}
