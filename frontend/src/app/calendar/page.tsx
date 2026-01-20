"use client";

import { useEffect, useState, useMemo } from "react";
import {
  ChevronLeft,
  ChevronRight,
  User,
  FolderKanban,
  Calendar as CalendarIcon,
} from "lucide-react";
import Header from "@/components/layout/header";
import LoadingSpinner from "@/components/common/loading-spinner";
import { getTasks, getTaskAssignees, getTaskProjects } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Task, TaskStatus } from "@/lib/types";

type DateType = "due_date" | "start_date" | "completed_date";

const dateTypeOptions: { label: string; value: DateType }[] = [
  { label: "Due Date", value: "due_date" },
  { label: "Start Date", value: "start_date" },
  { label: "Completed", value: "completed_date" },
];

const statusColors: Record<TaskStatus, string> = {
  assigned: "bg-blue-100 text-blue-800 border-blue-200",
  in_progress: "bg-yellow-100 text-yellow-800 border-yellow-200",
  on_hold: "bg-gray-100 text-gray-800 border-gray-200",
  done: "bg-green-100 text-green-800 border-green-200",
};

const priorityIndicators: Record<string, string> = {
  urgent: "border-l-4 border-l-red-500",
  high: "border-l-4 border-l-orange-500",
  medium: "border-l-4 border-l-yellow-500",
  low: "border-l-4 border-l-gray-400",
};

export default function CalendarPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [dateType, setDateType] = useState<DateType>("due_date");
  const [assigneeFilter, setAssigneeFilter] = useState<string>("");
  const [assignees, setAssignees] = useState<string[]>([]);
  const [projectFilter, setProjectFilter] = useState<string>("");
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  useEffect(() => {
    loadAssignees();
    loadProjects();
  }, []);

  useEffect(() => {
    loadTasks();
  }, [assigneeFilter, projectFilter]);

  const loadAssignees = async () => {
    try {
      const response = await getTaskAssignees();
      if (response.status && response.data) {
        setAssignees(response.data);
      }
    } catch (error) {
      console.error("Failed to load assignees", error);
    }
  };

  const loadProjects = async () => {
    try {
      const response = await getTaskProjects();
      if (response.status && response.data) {
        setProjects(response.data);
      }
    } catch (error) {
      console.error("Failed to load projects", error);
    }
  };

  const loadTasks = async () => {
    setLoading(true);
    try {
      const response = await getTasks({
        assigned_to: assigneeFilter || undefined,
        project: projectFilter || undefined,
        limit: 500, // Get more tasks for calendar view
      });
      if (response.status && response.data) {
        setTasks(response.data.tasks);
      }
    } catch (error) {
      console.error("Failed to load tasks", error);
    } finally {
      setLoading(false);
    }
  };

  // Get calendar data
  const calendarData = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    // First day of month
    const firstDay = new Date(year, month, 1);
    const startDay = firstDay.getDay(); // 0 = Sunday

    // Last day of month
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();

    // Previous month days to show
    const prevMonth = new Date(year, month, 0);
    const prevMonthDays = prevMonth.getDate();

    // Build calendar grid
    const days: { date: Date; isCurrentMonth: boolean }[] = [];

    // Previous month days
    for (let i = startDay - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month - 1, prevMonthDays - i),
        isCurrentMonth: false,
      });
    }

    // Current month days
    for (let i = 1; i <= daysInMonth; i++) {
      days.push({
        date: new Date(year, month, i),
        isCurrentMonth: true,
      });
    }

    // Next month days to complete the grid (6 rows)
    const remainingDays = 42 - days.length;
    for (let i = 1; i <= remainingDays; i++) {
      days.push({
        date: new Date(year, month + 1, i),
        isCurrentMonth: false,
      });
    }

    return days;
  }, [currentDate]);

  // Group tasks by date
  const tasksByDate = useMemo(() => {
    const grouped: Record<string, Task[]> = {};

    tasks.forEach((task) => {
      let dateStr: string | undefined;

      switch (dateType) {
        case "start_date":
          dateStr = task.start_date;
          break;
        case "completed_date":
          dateStr = task.completed_date;
          break;
        case "due_date":
        default:
          dateStr = task.due_date;
          break;
      }

      if (dateStr) {
        const date = new Date(dateStr);
        const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
        if (!grouped[key]) {
          grouped[key] = [];
        }
        grouped[key].push(task);
      }
    });

    return grouped;
  }, [tasks, dateType]);

  const goToPreviousMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const goToNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const formatDateKey = (date: Date) => {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  };

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  return (
    <div className="flex flex-col h-full">
      <Header title="Calendar" />

      <div className="flex-1 p-6 overflow-auto">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
          {/* Date Type Selector */}
          <div className="flex items-center gap-2">
            <CalendarIcon className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-500">Show by:</span>
            <div className="flex bg-gray-100 rounded-lg p-1">
              {dateTypeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setDateType(option.value)}
                  className={cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    dateType === option.value
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-4">
            {/* Assignee Filter */}
            {assignees.length > 0 && (
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-gray-500" />
                <select
                  value={assigneeFilter}
                  onChange={(e) => setAssigneeFilter(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">All assignees</option>
                  {assignees.map((assignee) => (
                    <option key={assignee} value={assignee}>
                      {assignee}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Project Filter */}
            {projects.length > 0 && (
              <div className="flex items-center gap-2">
                <FolderKanban className="w-4 h-4 text-gray-500" />
                <select
                  value={projectFilter}
                  onChange={(e) => setProjectFilter(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">All projects</option>
                  {projects.map((project) => (
                    <option key={project} value={project}>
                      {project}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Calendar Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-semibold text-gray-900">
              {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
            </h2>
            <button
              onClick={goToToday}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Today
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={goToPreviousMonth}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={goToNextMonth}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {/* Day Headers */}
            <div className="grid grid-cols-7 border-b border-gray-200">
              {dayNames.map((day) => (
                <div
                  key={day}
                  className="py-3 text-center text-sm font-medium text-gray-500 bg-gray-50"
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7">
              {calendarData.map((day, index) => {
                const dateKey = formatDateKey(day.date);
                const dayTasks = tasksByDate[dateKey] || [];
                const hasMoreTasks = dayTasks.length > 3;

                return (
                  <div
                    key={index}
                    className={cn(
                      "min-h-[120px] border-b border-r border-gray-100 p-1",
                      !day.isCurrentMonth && "bg-gray-50"
                    )}
                  >
                    <div
                      className={cn(
                        "text-sm font-medium mb-1 w-7 h-7 flex items-center justify-center rounded-full",
                        isToday(day.date) && "bg-primary-600 text-white",
                        !isToday(day.date) && day.isCurrentMonth && "text-gray-900",
                        !isToday(day.date) && !day.isCurrentMonth && "text-gray-400"
                      )}
                    >
                      {day.date.getDate()}
                    </div>

                    {/* Tasks */}
                    <div className="space-y-1">
                      {dayTasks.slice(0, 3).map((task) => (
                        <button
                          key={task.id}
                          onClick={() => setSelectedTask(task)}
                          className={cn(
                            "w-full text-left px-1.5 py-0.5 text-xs rounded truncate border",
                            statusColors[task.status],
                            priorityIndicators[task.priority]
                          )}
                          title={task.title}
                        >
                          {task.title}
                        </button>
                      ))}
                      {hasMoreTasks && (
                        <button
                          onClick={() => {
                            // Could show a modal with all tasks for this day
                            setSelectedTask(dayTasks[0]);
                          }}
                          className="w-full text-left px-1.5 py-0.5 text-xs text-gray-500 hover:text-gray-700"
                        >
                          +{dayTasks.length - 3} more
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Status:</span>
            <span className={cn("px-2 py-0.5 rounded border", statusColors.assigned)}>Assigned</span>
            <span className={cn("px-2 py-0.5 rounded border", statusColors.in_progress)}>In Progress</span>
            <span className={cn("px-2 py-0.5 rounded border", statusColors.on_hold)}>On Hold</span>
            <span className={cn("px-2 py-0.5 rounded border", statusColors.done)}>Done</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Priority:</span>
            <span className="px-2 py-0.5 rounded border-l-4 border-l-red-500 border border-gray-200">Urgent</span>
            <span className="px-2 py-0.5 rounded border-l-4 border-l-orange-500 border border-gray-200">High</span>
            <span className="px-2 py-0.5 rounded border-l-4 border-l-yellow-500 border border-gray-200">Medium</span>
            <span className="px-2 py-0.5 rounded border-l-4 border-l-gray-400 border border-gray-200">Low</span>
          </div>
        </div>
      </div>

      {/* Task Detail Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  );
}

function TaskDetailModal({
  task,
  onClose,
}: {
  task: Task;
  onClose: () => void;
}) {
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "Not set";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-md mx-4 p-6">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">{task.title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            &times;
          </button>
        </div>

        <div className="space-y-3">
          {task.description && (
            <div>
              <p className="text-sm text-gray-500">Description</p>
              <p className="text-gray-900">{task.description}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <span
                className={cn(
                  "inline-block px-2 py-1 text-sm rounded border",
                  statusColors[task.status]
                )}
              >
                {task.status.replace("_", " ")}
              </span>
            </div>

            <div>
              <p className="text-sm text-gray-500">Priority</p>
              <span className="text-gray-900 capitalize">{task.priority}</span>
            </div>
          </div>

          {task.assigned_to && (
            <div>
              <p className="text-sm text-gray-500">Assigned To</p>
              <p className="text-gray-900">{task.assigned_to}</p>
            </div>
          )}

          {task.project && (
            <div>
              <p className="text-sm text-gray-500">Project</p>
              <p className="text-gray-900">{task.project}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Start Date</p>
              <p className="text-gray-900">{formatDate(task.start_date)}</p>
            </div>

            <div>
              <p className="text-sm text-gray-500">Due Date</p>
              <p className="text-gray-900">{formatDate(task.due_date)}</p>
            </div>
          </div>

          {task.completed_date && (
            <div>
              <p className="text-sm text-gray-500">Completed Date</p>
              <p className="text-gray-900">{formatDate(task.completed_date)}</p>
            </div>
          )}

          {task.source_url && (
            <div>
              <p className="text-sm text-gray-500">Source</p>
              <a
                href={task.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700"
              >
                View in {task.source_type || "source"}
              </a>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Close
          </button>
          <a
            href={`/tasks?id=${task.id}`}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            View Task
          </a>
        </div>
      </div>
    </div>
  );
}
