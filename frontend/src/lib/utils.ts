import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNow, isToday, isTomorrow, isPast } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  const d = new Date(date);
  if (isToday(d)) {
    return `Today at ${format(d, "h:mm a")}`;
  }
  if (isTomorrow(d)) {
    return `Tomorrow at ${format(d, "h:mm a")}`;
  }
  return format(d, "MMM d, yyyy h:mm a");
}

export function formatDateShort(date: string | Date): string {
  const d = new Date(date);
  if (isToday(d)) {
    return "Today";
  }
  if (isTomorrow(d)) {
    return "Tomorrow";
  }
  return format(d, "MMM d");
}

export function formatRelativeTime(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function isOverdue(date: string | Date): boolean {
  return isPast(new Date(date));
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "done":
      return "bg-green-100 text-green-800";
    case "in_progress":
      return "bg-blue-100 text-blue-800";
    case "on_hold":
      return "bg-yellow-100 text-yellow-800";
    case "assigned":
      return "bg-gray-100 text-gray-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

export function getPriorityColor(priority: string): string {
  switch (priority) {
    case "urgent":
      return "bg-red-100 text-red-800";
    case "high":
      return "bg-orange-100 text-orange-800";
    case "medium":
      return "bg-blue-100 text-blue-800";
    case "low":
      return "bg-gray-100 text-gray-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

export function getStatusLabel(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getPriorityLabel(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}
