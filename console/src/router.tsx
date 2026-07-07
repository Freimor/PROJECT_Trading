import { createBrowserRouter, Navigate } from "react-router-dom";
import AdminLayout from "./layouts/AdminLayout";
import BenchmarkPage from "./pages/BenchmarkPage";
import ControlPage from "./pages/ControlPage";
import CryptoWorkspacePage from "./pages/CryptoWorkspacePage";
import EventsPage from "./pages/EventsPage";
import LlmAuditPage from "./pages/LlmAuditPage";
import MoexWorkspacePage from "./pages/MoexWorkspacePage";
import OverviewPage from "./pages/OverviewPage";
import PaperPage from "./pages/PaperPage";
import WorkflowsPage from "./pages/WorkflowsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AdminLayout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "crypto", element: <CryptoWorkspacePage /> },
      { path: "moex", element: <MoexWorkspacePage /> },
      { path: "events", element: <EventsPage /> },
      { path: "llm", element: <LlmAuditPage /> },
      { path: "paper", element: <PaperPage /> },
      { path: "benchmark", element: <BenchmarkPage /> },
      { path: "workflows", element: <WorkflowsPage /> },
      { path: "control", element: <ControlPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
