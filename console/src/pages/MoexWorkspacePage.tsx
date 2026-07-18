import { useOutletContext } from "react-router-dom";
import SecuritiesAutomationWorkspace from "../components/securities/SecuritiesAutomationWorkspace";
import type { AdminLayoutContext } from "../layouts/AdminLayout";

export default function MoexWorkspacePage() {
  const { overview } = useOutletContext<AdminLayoutContext>();

  return (
    <div className="page workspace crypto-automation-page">
      <SecuritiesAutomationWorkspace killSwitch={Boolean(overview?.kill_switch)} />
    </div>
  );
}
