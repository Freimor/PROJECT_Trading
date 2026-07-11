import { Button, ListBox, ListBoxItem, Popover, Select, SelectValue } from "react-aria-components";
import { useI18n, type Lang } from "../i18n/LanguageContext";
import Hint from "../ui/Hint";

type Props = {
  onRefresh: () => void;
  onToggleFeed: () => void;
  feedOpen: boolean;
};

export default function SidebarFooterActions({ onRefresh, onToggleFeed, feedOpen }: Props) {
  const { t, lang, setLang } = useI18n();

  return (
    <div className="sidebar-footer-actions">
      <Hint label={feedOpen ? t("shell.feedClose") : t("shell.feedOpen")}>
        <Button
          className={`topbar-btn sidebar-footer-btn ${feedOpen ? "active" : ""}`}
          onPress={onToggleFeed}
        >
          {t("shell.feedToggle")}
        </Button>
      </Hint>

      <Select
        className="lang-picker sidebar-footer-lang"
        aria-label={t("header.language")}
        selectedKey={lang}
        onSelectionChange={(key) => setLang(key as Lang)}
      >
        <Button className="lang-picker-trigger sidebar-footer-btn">
          <SelectValue />
          <span aria-hidden>▾</span>
        </Button>
        <Popover className="lang-picker-popover" placement="top start">
          <ListBox>
            <ListBoxItem id="ru">{t("lang.ru")}</ListBoxItem>
            <ListBoxItem id="en">{t("lang.en")}</ListBoxItem>
          </ListBox>
        </Popover>
      </Select>

      <Hint label={t("header.refreshHint")}>
        <Button className="topbar-btn primary sidebar-footer-btn" onPress={onRefresh}>
          {t("header.refresh")}
        </Button>
      </Hint>
    </div>
  );
}
