import { Button } from "react-aria-components";
import { useI18n } from "../i18n/LanguageContext";
import Hint from "../ui/Hint";

type Props = {
  onToggleNav: () => void;
};

export default function AppTopBar({ onToggleNav }: Props) {
  const { t } = useI18n();

  return (
    <header className="app-topbar">
      <div className="topbar-start">
        <Hint label={t("shell.toggleNav")}>
          <Button className="icon-btn" onPress={onToggleNav} aria-label={t("shell.toggleNav")}>
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden>
              <path
                d="M4 7h16M4 12h16M4 17h16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </Button>
        </Hint>
      </div>
    </header>
  );
}
