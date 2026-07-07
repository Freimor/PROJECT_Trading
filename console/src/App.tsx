import { RouterProvider } from "react-router-dom";
import { ErrorNotificationsProvider } from "./context/ErrorNotifications";
import { LanguageProvider } from "./i18n/LanguageContext";
import { router } from "./router";

export default function App() {
  return (
    <LanguageProvider>
      <ErrorNotificationsProvider>
        <RouterProvider router={router} />
      </ErrorNotificationsProvider>
    </LanguageProvider>
  );
}
