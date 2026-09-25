import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "../../lib/utils";

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold leading-none tabular-nums",
  {
    variants: {
      variant: {
        neutral: "border-border bg-muted text-muted-foreground",
        evidence: "border-evidence/20 bg-evidence/10 text-evidence",
        success: "border-success/20 bg-success/10 text-success",
        attention:
          "border-attention/30 bg-attention/12 text-attention-foreground",
        destructive: "border-destructive/20 bg-destructive/10 text-destructive",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

type BadgeProps = ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean };

function Badge({ className, variant, asChild = false, ...props }: BadgeProps) {
  const Component = asChild ? Slot : "span";
  return (
    <Component
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}

export { Badge };
