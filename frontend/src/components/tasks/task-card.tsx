"use client";

import { Calendar, CalendarCheck, CalendarClock, Tag, User, ExternalLink, Repeat } from "lucide-react";
import { cn, formatDateShort, isOverdue, getPriorityColor, getPriorityLabel } from "@/lib/utils";
import TaskStatusBadge from "./task-status-badge";
import type { Task } from "@/lib/types";

interface TaskCardProps {
  task: Task;
  onClick?: () => void;
}

export default function TaskCard({ task, onClick }: TaskCardProps) {
  const overdue = task.due_date && task.status !== "done" && isOverdue(task.due_date);

  return (
    <div
      onClick={onClick}
      className={cn(
        "bg-white border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer",
        overdue && "border-red-300 bg-red-50"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-gray-900 truncate">{task.title}</h3>
          {task.description && (
            <p className="text-sm text-gray-500 mt-1 line-clamp-2">
              {task.description}
            </p>
          )}
        </div>
        <TaskStatusBadge status={task.status} />
      </div>

      <div className="mt-3 flex items-center flex-wrap gap-3 text-sm">
        {/* Priority */}
        <span
          className={cn(
            "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
            getPriorityColor(task.priority)
          )}
        >
          {getPriorityLabel(task.priority)}
        </span>

        {/* Start Date */}
        {task.start_date && (
          <span className="inline-flex items-center gap-1 text-gray-500">
            <CalendarClock className="w-3.5 h-3.5" />
            <span className="text-xs">Started:</span> {formatDateShort(task.start_date)}
          </span>
        )}

        {/* Due Date */}
        {task.due_date && (
          <span
            className={cn(
              "inline-flex items-center gap-1 text-gray-500",
              overdue && "text-red-600 font-medium"
            )}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span className="text-xs">Due:</span> {formatDateShort(task.due_date)}
          </span>
        )}

        {/* Completed Date */}
        {task.completed_date && (
          <span className="inline-flex items-center gap-1 text-green-600">
            <CalendarCheck className="w-3.5 h-3.5" />
            <span className="text-xs">Done:</span> {formatDateShort(task.completed_date)}
          </span>
        )}

        {/* Assigned To */}
        {task.assigned_to && (
          <span className="inline-flex items-center gap-1 text-gray-500">
            <User className="w-3.5 h-3.5" />
            {task.assigned_to}
          </span>
        )}

        {/* Tags */}
        {task.tags && task.tags.length > 0 && (
          <span className="inline-flex items-center gap-1 text-gray-500">
            <Tag className="w-3.5 h-3.5" />
            {task.tags.slice(0, 2).join(", ")}
            {task.tags.length > 2 && ` +${task.tags.length - 2}`}
          </span>
        )}

        {/* Recurring indicator */}
        {task.is_recurring && (
          <span className="inline-flex items-center gap-1 text-xs text-purple-600" title="Recurring task">
            <Repeat className="w-3 h-3" />
            {task.recurrence_type}
          </span>
        )}

        {/* Source - Taiga link */}
        {task.source_type === "taiga" && task.source_url && (
          <a
            href={task.source_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline"
          >
            <ExternalLink className="w-3 h-3" />
            View in Taiga
          </a>
        )}
        {/* Other sources */}
        {task.source_type && task.source_type !== "taiga" && (
          <span className="text-xs text-gray-400">
            via {task.source_type}
          </span>
        )}
      </div>
    </div>
  );
}
