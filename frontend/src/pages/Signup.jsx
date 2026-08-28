import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "../components/Logo";

export default function Signup() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("consumer");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const roles = [
    {
      value: "consumer",
      label: "Consumer",
      icon: "🛒",
      badge: "Shopper / Citizen",
      description: "Audit packaged foods, verify Legal Metrology declarations & compare unit prices.",
    },
    {
      value: "brand",
      label: "Brand Owner",
      icon: "🏢",
      badge: "FMCG / Manufacturer",
      description: "Pre-screen packaging artwork proofs, manage SKU catalogs & generate certificates.",
    },
    {
      value: "regulator",
      label: "Regulator",
      icon: "⚖️",
      badge: "Legal Metrology Officer",
      description: "Track violation heatmaps, review consumer grievance reports & monitor compliance.",
    },
    {
      value: "admin",
      label: "Administrator",
      icon: "⚙️",
      badge: "System Admin",
      description: "Full platform governance, rule weights configuration & system audit logs.",
    },
  ];

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await signUp(email, password, fullName, role);
      if (!data.session) {
        setEmailSent(true);
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err.message || "Failed to create account. Please verify input data.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 px-4 py-8 antialiased">
      <div className="max-w-2xl w-full mx-auto card-slate bg-white p-6 sm:p-10 shadow-2xl border-slate-200">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-3">
            <Logo variant="full" to="/" showBadge={false} />
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">Create Your Account</h2>
          <p className="text-xs text-slate-500 mt-1">
            Choose your role to get started with AI Legal Metrology verification
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {emailSent && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 p-4 rounded-xl text-xs font-medium space-y-1">
              <p className="font-bold">✓ Activation Link Sent!</p>
              <p>We sent a confirmation email to <strong>{email}</strong>. Click the link in your email to activate your account, then sign in.</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 p-3 rounded-xl text-xs font-bold flex items-center gap-2">
              <span>⚠️</span> {error}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                className="input-field text-xs"
                placeholder="Dr. Rajesh Sharma"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input-field text-xs"
                placeholder="rajesh@example.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="input-field text-xs"
              placeholder="Minimum 6 characters"
            />
          </div>

          {/* Role Selection Cards */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">
              Select Your Application Role
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {roles.map((r) => (
                <button
                  type="button"
                  key={r.value}
                  onClick={() => setRole(r.value)}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    role === r.value
                      ? "border-emerald-500 bg-emerald-50/60 shadow-xs ring-1 ring-emerald-500"
                      : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-sm">{r.icon}</span>
                    <span className="text-[9px] font-bold text-slate-500 uppercase">{r.badge}</span>
                  </div>
                  <h4 className="text-xs font-black text-slate-900">{r.label}</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5 leading-snug">{r.description}</p>
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-accent w-full py-3.5 text-xs font-black uppercase tracking-wider disabled:opacity-50 shadow-md"
          >
            {loading ? "Creating Account..." : "Complete Registration"}
          </button>
        </form>

        <p className="text-center mt-6 text-xs text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="text-emerald-700 hover:text-emerald-800 font-extrabold">
            Sign In Here →
          </Link>
        </p>
      </div>
    </div>
  );
}
