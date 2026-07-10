import { Button, ListBox, ListBoxItem, Popover, Select, SelectValue } from "react-aria-components";
import { useI18n, type Lang } from "../i18n/LanguageContext";
import Hint from "../ui/Hint";

type Props = {
  onRefresh: () => void;
  onToggleNav: () => void;
  onToggleFeed: () => void;
  feedOpen: boolean;
};

export default function AppTopBar({ onRefresh, onToggleNav, onToggleFeed, feedOpen }: Props) {
  const { t, lang, setLang } = useI18n();

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

      <div className="topbar-actions">
        <Hint label={feedOpen ? t("shell.feedClose") : t("shell.feedOpen")}>
          <Button
            className={`topbar-btn ${feedOpen ? "active" : ""}`}
            onPress={onToggleFeed}
          >
            {t("shell.feedToggle")}
          </Button>
        </Hint>

        <Select
          className="lang-picker"
          aria-label={t("header.language")}
          selectedKey={lang}
          onSelectionChange={(key) => setLang(key as Lang)}
        >
          <Button className="lang-picker-trigger">
            <SelectValue />
            <span aria-hidden>▾</span>
          </Button>
          <Popover className="lang-picker-popover">
            <ListBox>
              <ListBoxItem id="ru">{t("lang.ru")}</ListBoxItem>
              <ListBoxItem id="en">{t("lang.en")}</ListBoxItem>
            </ListBox>
          </Popover>
        </Select>

        <Hint label={t("header.refreshHint")}>
          <Button className="topbar-btn primary" onPress={onRefresh}>
            {t("header.refresh")}
          </Button>
        </Hint>
      </div>
    </header>
  );
}
