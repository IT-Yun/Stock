import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { t as translate, type Lang, type TranslationKey } from "./translations";

interface LanguageContextType {
  lang: Lang;
  toggleLang: () => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextType>({
  lang: "ko",
  toggleLang: () => {},
  t: (key) => translate(key, "ko"),
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => {
    const saved = localStorage.getItem("stock-lang");
    return (saved === "en" || saved === "ko") ? saved : "ko";
  });

  const toggleLang = useCallback(() => {
    setLang((prev) => {
      const next = prev === "ko" ? "en" : "ko";
      localStorage.setItem("stock-lang", next);
      return next;
    });
  }, []);

  const tFn = useCallback((key: TranslationKey) => translate(key, lang), [lang]);

  return (
    <LanguageContext.Provider value={{ lang, toggleLang, t: tFn }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
