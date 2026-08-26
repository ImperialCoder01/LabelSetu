import { useTranslation } from "react-i18next";

const LANGUAGES = [
  { code: "en", label: "English", flag: "EN" },
  { code: "hi", label: "हिन्दी", flag: "HI" },
];

export default function LanguageToggle() {
  const { i18n } = useTranslation();

  const handleChange = (code) => {
    i18n.changeLanguage(code);
    localStorage.setItem("lang", code);
  };

  return (
    <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
      {LANGUAGES.map((lang) => (
        <button
          key={lang.code}
          onClick={() => handleChange(lang.code)}
          className={
            "px-2.5 py-1 rounded-md text-xs font-semibold transition-colors " +
            (i18n.language === lang.code
              ? "bg-white text-primary-700 shadow-sm"
              : "text-gray-500 hover:text-gray-700")
          }
        >
          {lang.flag}
        </button>
      ))}
    </div>
  );
}
