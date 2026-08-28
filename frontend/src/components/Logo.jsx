import { Link } from "react-router-dom";

export default function Logo({ variant = "full", className = "", to = "/", showBadge = true }) {
  // variant options:
  // "full" -> dark text on light background
  // "dark" -> white text on dark background
  // "mark" -> standalone icon only (light)
  // "mark-dark" -> standalone icon only (dark)

  let src = "/branding/labelsetu-logo.svg";
  if (variant === "dark") src = "/branding/labelsetu-logo-dark.svg";
  else if (variant === "mark") src = "/branding/labelsetu-mark.svg";
  else if (variant === "mark-dark") src = "/branding/labelsetu-mark-dark.svg";

  const isMarkOnly = variant === "mark" || variant === "mark-dark";

  const content = (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      <img
        src={src}
        alt="LabelSetu"
        className={isMarkOnly ? "w-9 h-9 object-contain" : "h-9 w-auto object-contain"}
      />
      {showBadge && !isMarkOnly && (
        <span className="hidden xl:inline-block text-[9px] uppercase font-extrabold tracking-wider px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
          SIH 2026
        </span>
      )}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="inline-flex items-center focus:outline-none focus:ring-2 focus:ring-accent-500 rounded-lg">
        {content}
      </Link>
    );
  }

  return content;
}
