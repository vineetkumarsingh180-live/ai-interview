import type { LucideIcon } from 'lucide-react';

/** One selectable entry in the side navigation. Supplied by the app (composition root). */
export interface NavEntry {
  /** DOM id (kept stable for tests and automation). */
  id: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  active: boolean;
  onSelect: () => void;
}

export interface NavSection {
  label: string;
  entries: NavEntry[];
}
