import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTranslation } from "react-i18next";

export default function Signup() {
  const { t } = useTranslation();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("consumer");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const roles = [
    { value: "consumer", label: t("auth.roleConsumer"), description: t("auth.roleConsumerDesc") },
    { value: "brand", label: t("auth.roleBrand"), description: t("auth.roleBrandDesc") },
    { value: "regulator", label: t("auth.roleRegulator"), description: t("auth.roleRegulatorDesc") },
    { value: "admin", label: t("auth.roleAdmin"), description: t("auth.roleAdminDesc") },
  ];

  const [emailSent, setEmailSent] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await signUp(email, password, fullName, role);
      if (!data.session) {
        // Email confirmation required
        setEmailSent(true);
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err.message || "Failed to create account");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4 py-8">
      <div className="card-slate w-full max-w-md bg-white border-slate-200 shadow-xl p-8">
        <div className="text-center mb-6">
          <div className="w-12 h-12 bg-accent-600 rounded-xl flex items-center justify-center mx-auto mb-3 shadow-sm">
            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">{t("auth.createAccount")}</h1>
          <p className="text-xs text-slate-500 mt-1">LabelSetu AI Legal Metrology Verifier</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {emailSent && (
            <div className="bg-accent-50 border border-accent-200 text-accent-900 p-4 rounded-xl text-xs font-medium">
              <p className="font-bold">Check your email!</p>
              <p className="mt-1">We sent a confirmation link to <strong>{email}</strong>. Click the link to activate your account, then sign in.</p>
            </div>
          )}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 p-3 rounded-lg text-xs font-bold">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              {t("auth.fullName")}
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              className="input-field text-xs"
              placeholder="John Doe"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              {t("auth.email")}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="input-field text-xs"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              {t("auth.password")}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="input-field text-xs"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">
              Account Role
            </label>
            <div className="grid grid-cols-2 gap-2">
              {roles.map((r) => (
                <button
                  type="button"
                  key={r.value}
                  onClick={() => setRole(r.value)}
                  className={`p-2.5 rounded-lg border text-left text-xs transition-all ${
                    role === r.value
                      ? "border-accent-500 bg-accent-50/50 text-accent-900 font-bold shadow-sm"
                      : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <div className="font-bold">{r.label}</div>
                  <div className="text-[10px] text-slate-500 font-normal leading-tight mt-0.5">{r.description}</div>
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-accent w-full py-3 text-sm disabled:opacity-50"
          >
            {loading ? t("auth.creatingAccount") : t("common.signUp")}
          </button>
        </form>

        <p className="text-center mt-6 text-xs text-slate-500">
          {t("auth.alreadyHaveAccount")}{" "}
          <Link to="/login" className="text-accent-700 hover:text-accent-800 font-bold">
            {t("common.signIn")}
          </Link>
        </p>
      </div>
    </div>
  );
}
