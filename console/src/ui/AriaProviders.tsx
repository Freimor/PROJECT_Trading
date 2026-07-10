import type { ReactNode } from "react";
import { RouterProvider as AriaRouterProvider } from "react-aria-components";
import { useHref, useNavigate } from "react-router-dom";

export default function AriaProviders({ children }: { children: ReactNode }) {
  const navigate = useNavigate();

  return (
    <AriaRouterProvider navigate={navigate} useHref={useHref}>
      {children}
    </AriaRouterProvider>
  );
}
