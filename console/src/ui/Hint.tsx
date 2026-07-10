import type { ReactNode } from "react";
import { Tooltip, TooltipTrigger } from "react-aria-components";

type Props = {
  label: string;
  children: ReactNode;
  delay?: number;
};

export default function Hint({ label, children, delay = 500 }: Props) {
  if (!label) return <>{children}</>;

  return (
    <TooltipTrigger delay={delay} closeDelay={100}>
      {children}
      <Tooltip className="ui-tooltip" offset={10}>
        {label}
      </Tooltip>
    </TooltipTrigger>
  );
}
