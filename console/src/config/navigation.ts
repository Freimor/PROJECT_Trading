import type { ComponentType } from "react";
import {
  IconBenchmark,
  IconControl,
  IconCrypto,
  IconEvents,
  IconLlm,
  IconMoex,
  IconNews,
  IconOverview,
  IconResearch,
  IconWorkflows,
} from "../ui/icons";

export type NavIcon = ComponentType<{ className?: string }>;

export type NavItemDef = {
  to: string;
  end?: boolean;
  labelKey: string;
  hintKey: string;
  icon: NavIcon;
};

export type NavGroupDef = {
  groupKey: string;
  items: NavItemDef[];
};

export const NAV_GROUPS: NavGroupDef[] = [
  {
    groupKey: "nav.groups.trading",
    items: [
      {
        to: "/",
        end: true,
        labelKey: "nav.overview",
        hintKey: "nav.overviewHint",
        icon: IconOverview,
      },
      {
        to: "/crypto",
        labelKey: "nav.crypto",
        hintKey: "nav.cryptoHint",
        icon: IconCrypto,
      },
      {
        to: "/moex",
        labelKey: "nav.moex",
        hintKey: "nav.moexHint",
        icon: IconMoex,
      },
    ],
  },
  {
    groupKey: "nav.groups.analytics",
    items: [
      {
        to: "/news",
        labelKey: "nav.news",
        hintKey: "nav.newsHint",
        icon: IconNews,
      },
      {
        to: "/events",
        labelKey: "nav.events",
        hintKey: "nav.eventsHint",
        icon: IconEvents,
      },
      {
        to: "/llm",
        labelKey: "nav.llm",
        hintKey: "nav.llmHint",
        icon: IconLlm,
      },
      {
        to: "/benchmark",
        labelKey: "nav.benchmark",
        hintKey: "nav.benchmarkHint",
        icon: IconBenchmark,
      },
    ],
  },
  {
    groupKey: "nav.groups.tools",
    items: [
      {
        to: "/research",
        labelKey: "nav.research",
        hintKey: "nav.researchHint",
        icon: IconResearch,
      },
      {
        to: "/workflows",
        labelKey: "nav.workflows",
        hintKey: "nav.workflowsHint",
        icon: IconWorkflows,
      },
    ],
  },
  {
    groupKey: "nav.groups.system",
    items: [
      {
        to: "/control",
        labelKey: "nav.control",
        hintKey: "nav.controlHint",
        icon: IconControl,
      },
    ],
  },
];
