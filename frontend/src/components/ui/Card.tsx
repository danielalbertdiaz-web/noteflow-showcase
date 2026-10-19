import React from "react";
import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: "none" | "sm" | "md" | "lg";
  shadow?: "none" | "sm" | "md" | "lg";
  border?: boolean;
}

const paddingClasses = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

const shadowClasses = {
  none: "",
  sm: "shadow-sm",
  md: "shadow-md",
  lg: "shadow-lg",
};

export function Card({
  children,
  className,
  padding = "md",
  shadow = "sm",
  border = true,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl bg-white",
        border && "border border-gray-200",
        paddingClasses[padding],
        shadowClasses[shadow],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
}

export function CardHeader({
  title,
  subtitle,
  action,
  children,
  className,
  ...props
}: CardHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 pb-4",
        className
      )}
      {...props}
    >
      <div className="min-w-0 flex-1">
        {title && (
          <h3 className="text-base font-semibold text-gray-900 leading-tight">
            {title}
          </h3>
        )}
        {subtitle && (
          <p className="mt-0.5 text-sm text-gray-500">{subtitle}</p>
        )}
        {children}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function CardBody({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("", className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "mt-4 flex items-center justify-end gap-3 border-t border-gray-100 pt-4",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// Collapsible card section used in SOAP notes
interface CollapsibleCardProps {
  title: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
  badge?: React.ReactNode;
}

export function CollapsibleCard({
  title,
  icon,
  defaultOpen = true,
  children,
  className,
  badge,
}: CollapsibleCardProps) {
  const [open, setOpen] = React.useState(defaultOpen);

  return (
    <div
      className={cn(
        "rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden",
        className
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2">
          {icon && (
            <span className="text-brand-600 shrink-0">{icon}</span>
          )}
          <span className="font-semibold text-gray-900">{title}</span>
          {badge && <span>{badge}</span>}
        </div>
        <svg
          className={cn(
            "h-5 w-5 text-gray-400 transition-transform duration-200 shrink-0",
            open && "rotate-180"
          )}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>
      {open && <div className="px-4 pb-4 pt-2">{children}</div>}
    </div>
  );
}
