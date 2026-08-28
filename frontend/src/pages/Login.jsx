import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "../components/Logo";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [selectedRolePreview, setSelectedRolePreview] = useState("consumer");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await signIn(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  }

  const roleProfiles = [
    {
      id: "consumer",
      title: "Consumer Audit",
      icon: "🛒",
      desc: "Audit packaged foods, cosmetics & groceries against Legal Metrology 2011 rules.",
      badge: "Citizen & Shopper",
    },
    {
      id: "brand",
      title: "Brand SaaS",
      icon: "🏢",
      desc: "Pre-market packaging artwork QA, bulk label scans & compliance certificates.",
      badge: "Manufacturer / D2C",
    },
    {
      id: "regulator",
      title: "Regulator Portal",
      icon: "⚖️",
      desc: "Ecosystem-wide compliance telemetry, violation heatmaps & grievance review.",
      badge: "Enforcement Officer",
    },
    {
      id: "admin",
      title: "Admin Control",
      icon: "⚙️",
      desc: "Legal Metrology rule weight configs, user management & system audit logs.",
      badge: "Platform Admin",
    },
  ];

  return (
    <div className="min-h-screen flex flex-col justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 px-4 py-8 antialiased">
      <div className="max-w-4xl w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left Side: Brand Proposition & Value Statements */}
        <div className="lg:col-span-5 text-white space-y-6 text-center lg:text-left">
          <div className="inline-flex items-center gap-2">
            <Logo variant="dark" to="/" showBadge={true} />
          </div>

          <div>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white leading-tight">
              Verify. Understand. <span className="text-emerald-400">Act.</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
              India’s AI-assisted Legal Metrology compliance verification platform for packaged commodities.
            </p>
          </div>

          {/* 4 Role Showcase Grid */}
          <div className="grid grid-cols-2 gap-2.5 text-left pt-2">
            {roleProfiles.map((r) => (
              <div
                key={r.id}
                onClick={() => setSelectedRolePreview(r.id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer ${
                  selectedRolePreview === r.id
                    ? "bg-slate-800/90 border-emerald-500 shadow-xs"
                    : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-sm">{r.icon}</span>
                  <span className="text-[9px] font-bold text-slate-400 uppercase">{r.badge}</span>
                </div>
                <h4 className="text-xs font-black text-white">{r.title}</h4>
                <p className="text-[10px] text-slate-400 mt-0.5 leading-snug line-clamp-2">{r.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Right Side: Clean Sign In Form */}
        <div className="lg:col-span-7 card-slate bg-white p-6 sm:p-8 shadow-2xl border-slate-200">
          <div className="mb-6">
            <h3 className="text-xl font-black text-slate-900 tracking-tight">Sign In to LabelSetu</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Access your role-specific dashboard & verified scan repository
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-800 p-3 rounded-xl text-xs font-bold flex items-center gap-2">
                <span>⚠️</span> {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
                Account Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input-field text-xs"
                placeholder="name@example.com"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide">
                  Password
                </label>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="input-field text-xs"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-accent w-full py-3 text-xs font-black uppercase tracking-wider disabled:opacity-50 shadow-md"
            >
              {loading ? "Authenticating Session..." : "Sign In to Dashboard"}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-500">Need a new account?</span>
            <Link to="/signup" className="text-emerald-700 hover:text-emerald-800 font-extrabold">
              Create Free Account →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
