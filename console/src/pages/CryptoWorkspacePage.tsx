import { useOutletContext } from "react-router-dom";
import CryptoAutomationWorkspace from "../components/crypto/CryptoAutomationWorkspace";
import type { AdminLayoutContext } from "../layouts/AdminLayout";

export default function CryptoWorkspacePage() {
  const { overview } = useOutletContext<AdminLayoutContext>();

  return (
    <div className="page workspace crypto-automation-page">
      <CryptoAutomationWorkspace killSwitch={Boolean(overview?.kill_switch)} />
    </div>
  );
}
