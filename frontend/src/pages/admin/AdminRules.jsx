import { useState, useEffect } from "react";
import { supabase } from "../../lib/supabase";

const API_BASE = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function KeywordInput({ keywords, onChange }) {
  const [input, setInput] = useState("");
  const add = () => {
    const val = input.trim().toLowerCase();
    if (val && !keywords.includes(val)) {
      onChange([...keywords, val]);
      setInput("");
    }
  };
  const remove = (kw) => onChange(keywords.filter((k) => k !== kw));
  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {keywords.map((kw) => (
          <span key={kw} className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
            {kw}
            <button onClick={() => remove(kw)} className="text-gray-400 hover:text-red-500 ml-0.5">&times;</button>
          </span>
        ))}
        {keywords.length === 0 && <span className="text-xs text-gray-400">No keywords</span>}
      </div>
      <div className="flex gap-1.5">
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())} placeholder="Add keyword..." className="input-field text-xs py-1.5 flex-1" />
        <button onClick={add} className="px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded transition-colors">Add</button>
      </div>
    </div>
  );
}

function RuleCard({ field, index, onChange, saving }) {
  const severityColor = field.severity === "Critical" ? "bg-orange-100 text-orange-700 border-orange-300" : "bg-gray-100 text-gray-600 border-gray-300";
  const active = field.active !== false;
  return (
    <div className={`border-2 rounded-xl p-5 transition-all ${active ? "bg-white border-gray-200" : "bg-gray-50 border-gray-200 opacity-60"}`}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-gray-400 w-6 text-right">{index + 1}</span>
          <input value={field.name} onChange={(e) => onChange({ ...field, name: e.target.value })} className="text-sm font-semibold text-gray-900 border-b border-transparent hover:border-gray-300 focus:border-primary-500 focus:outline-none bg-transparent px-0 py-0.5 w-64 transition-colors" />
        </div>
        <div className="flex items-center gap-3">
          <select value={field.severity} onChange={(e) => onChange({ ...field, severity: e.target.value })} className={`text-xs px-2 py-1 rounded font-medium border cursor-pointer ${severityColor}`}>
            <option value="Critical">Critical</option>
            <option value="Minor">Minor</option>
          </select>
          <button onClick={() => onChange({ ...field, active: !active })} className={`relative w-10 h-5 rounded-full transition-colors ${active ? "bg-primary-500" : "bg-gray-300"}`} title={active ? "Active" : "Inactive"}>
            <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${active ? "translate-x-5" : ""}`} />
          </button>
        </div>
      </div>
      <div className="ml-9">
        <p className="text-xs text-gray-400 font-mono mb-2">ID: {field.id}</p>
        {field.description && <p className="text-xs text-gray-500 mb-3">{field.description}</p>}
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1.5">Keywords</p>
          <KeywordInput keywords={field.keywords || []} onChange={(kw) => onChange({ ...field, keywords: kw })} />
        </div>
      </div>
    </div>
  );
}

export default function AdminRules() {
  const [rules, setRules] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const [scoring, setScoring] = useState({ critical_weight: 15, minor_weight: 5 });

  useEffect(() => { fetchRules(); }, []);

  async function fetchRules() {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(API_BASE + "/api/admin/rules", {
        headers: { Authorization: "Bearer " + (session?.access_token || "") },
      });
      if (!res.ok) throw new Error("Failed to load rules");
      const data = await res.json();
      setRules(data);
      setScoring(data.scoring || { critical_weight: 15, minor_weight: 5 });
    } catch (err) {
      setSaveMsg({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  const updateField = (index, updated) => {
    const newFields = [...rules.fields];
    newFields[index] = updated;
    setRules({ ...rules, fields: newFields });
  };

  const activeCount = rules ? rules.fields.filter((f) => f.active !== false).length : 0;

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(API_BASE + "/api/admin/rules", {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + (session?.access_token || "") },
        body: JSON.stringify({ rules: { ...rules, scoring }, change_summary: "Admin updated rules via dashboard" }),
      });
      if (!res.ok) throw new Error("Failed to save rules");
      setSaveMsg({ type: "success", text: "Rules saved successfully. Audit log entry created." });
      setTimeout(() => setSaveMsg(null), 4000);
    } catch (err) {
      setSaveMsg({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="space-y-4"><div className="h-8 bg-gray-200 rounded animate-pulse w-64" /><div className="h-40 bg-gray-200 rounded animate-pulse" /></div>;
  if (!rules) return <p className="text-red-600">Failed to load rules.</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compliance Rules</h1>
          <p className="text-gray-500 mt-1">{rules.fields.length} fields &middot; {activeCount} active &middot; v{rules.version}</p>
        </div>
        <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
          {saving && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
          {saving ? "Saving..." : "Save All Changes"}
        </button>
      </div>

      {saveMsg && (
        <div className={`p-3 rounded-lg text-sm ${saveMsg.type === "success" ? "bg-green-50 border border-green-200 text-green-700" : "bg-red-50 border border-red-200 text-red-700"}`}>{saveMsg.text}</div>
      )}

      <div className="space-y-4">
        {rules.fields.map((field, i) => (
          <RuleCard key={field.id} field={field} index={i} onChange={(f) => updateField(i, f)} saving={saving} />
        ))}
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Scoring Configuration</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Critical Field Penalty (pts)</label>
            <input type="number" value={scoring.critical_weight} onChange={(e) => setScoring({ ...scoring, critical_weight: parseInt(e.target.value) || 0 })} className="input-field w-32" />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Minor Field Penalty (pts)</label>
            <input type="number" value={scoring.minor_weight} onChange={(e) => setScoring({ ...scoring, minor_weight: parseInt(e.target.value) || 0 })} className="input-field w-32" />
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-3">Base score: 100. Each missing field deducts its penalty. Minimum: 0.</p>
      </div>
    </div>
  );
}
