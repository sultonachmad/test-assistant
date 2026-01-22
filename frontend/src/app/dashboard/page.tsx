"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle,
  Clock,
  AlertCircle,
  Calendar,
  Filter,
  User,
  FolderKanban,
  X,
} from "lucide-react";
import Header from "@/components/layout/header";
import LoadingSpinner from "@/components/common/loading-spinner";
import { getDashboard, getTasks, getTaskAssignees, getTaskProjects } from "@/lib/api";
import { useGoogleTokenSync } from "@/lib/use-google-token-sync";
import type { DashboardData, Task } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  // Filter states
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [startDateFrom, setStartDateFrom] = useState("");
  const [startDateTo, setStartDateTo] = useState("");
  const [dueDateFrom, setDueDateFrom] = useState("");
  const [dueDateTo, setDueDateTo] = useState("");
  const [completedDateFrom, setCompletedDateFrom] = useState("");
  const [completedDateTo, setCompletedDateTo] = useState("");
  const [assignees, setAssignees] = useState<string[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  const [filteredTasks, setFilteredTasks] = useState<Task[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);

  // Sync Google tokens to backend
  useGoogleTokenSync();

  useEffect(() => {
    loadDashboard();
    loadAssignees();
    loadProjects();
    loadFilteredTasks();
  }, []);

  // Reload tasks when filters change
  useEffect(() => {
    loadFilteredTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assigneeFilter, projectFilter, startDateFrom, startDateTo, dueDateFrom, dueDateTo, completedDateFrom, completedDateTo]);

  const loadDashboard = async () => {
    try {
      const response = await getDashboard();
      if (response.status && response.data) {
        setData(response.data);
      }
    } catch (error) {
      console.error("Failed to load dashboard", error);
    } finally {
      setLoading(false);
    }
  };

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

  const loadFilteredTasks = async () => {
    setTasksLoading(true);
    try {
      const response = await getTasks({
        assigned_to: assigneeFilter || undefined,
        project: projectFilter || undefined,
        limit: 500,
      });

      if (response.status && response.data) {
        let tasks = response.data.tasks || [];

        // Client-side date filtering (only filter if task has the date field)
        if (startDateFrom) {
          const fromDate = new Date(startDateFrom);
          fromDate.setHours(0, 0, 0, 0);
          tasks = tasks.filter(t => {
            if (!t.start_date) return false;
            const taskDate = new Date(t.start_date);
            return taskDate >= fromDate;
          });
        }
        if (startDateTo) {
          const toDate = new Date(startDateTo);
          toDate.setHours(23, 59, 59, 999);
          tasks = tasks.filter(t => {
            if (!t.start_date) return false;
            const taskDate = new Date(t.start_date);
            return taskDate <= toDate;
          });
        }
        if (dueDateFrom) {
          const fromDate = new Date(dueDateFrom);
          fromDate.setHours(0, 0, 0, 0);
          tasks = tasks.filter(t => {
            if (!t.due_date) return false;
            const taskDate = new Date(t.due_date);
            return taskDate >= fromDate;
          });
        }
        if (dueDateTo) {
          const toDate = new Date(dueDateTo);
          toDate.setHours(23, 59, 59, 999);
          tasks = tasks.filter(t => {
            if (!t.due_date) return false;
            const taskDate = new Date(t.due_date);
            return taskDate <= toDate;
          });
        }
        if (completedDateFrom) {
          const fromDate = new Date(completedDateFrom);
          fromDate.setHours(0, 0, 0, 0);
          tasks = tasks.filter(t => {
            if (!t.completed_date) return false;
            const taskDate = new Date(t.completed_date);
            return taskDate >= fromDate;
          });
        }
        if (completedDateTo) {
          const toDate = new Date(completedDateTo);
          toDate.setHours(23, 59, 59, 999);
          tasks = tasks.filter(t => {
            if (!t.completed_date) return false;
            const taskDate = new Date(t.completed_date);
            return taskDate <= toDate;
          });
        }

        setFilteredTasks(tasks);
      } else {
        setFilteredTasks([]);
      }
    } catch (error) {
      console.error("Failed to load tasks", error);
      setFilteredTasks([]);
    } finally {
      setTasksLoading(false);
    }
  };

  const clearFilters = () => {
    setAssigneeFilter("");
    setProjectFilter("");
    setStartDateFrom("");
    setStartDateTo("");
    setDueDateFrom("");
    setDueDateTo("");
    setCompletedDateFrom("");
    setCompletedDateTo("");
  };

  const hasActiveFilters = assigneeFilter || projectFilter || startDateFrom || startDateTo || dueDateFrom || dueDateTo || completedDateFrom || completedDateTo;

  // Calculate summary from filtered tasks
  const filteredSummary = {
    total: filteredTasks.length,
    done: filteredTasks.filter(t => t.status === "done").length,
    in_progress: filteredTasks.filter(t => t.status === "in_progress").length,
    on_hold: filteredTasks.filter(t => t.status === "on_hold").length,
    assigned: filteredTasks.filter(t => t.status === "assigned").length,
    overdue: filteredTasks.filter(t => t.due_date && t.status !== "done" && new Date(t.due_date) < new Date()).length,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">Failed to load dashboard</p>
      </div>
    );
  }

  // Use filtered summary for display
  const displaySummary = filteredSummary;

  return (
    <div className="flex flex-col h-full">
      <Header title="Dashboard" />

      <div className="flex-1 p-6 overflow-auto">
        {/* Filters Section */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-500" />
              <h2 className="text-sm font-semibold text-gray-900">
                Filter Dashboard
              </h2>
              {hasActiveFilters && (
                <span className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs rounded-full">
                  Filters Active
                </span>
              )}
            </div>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
              >
                <X className="w-4 h-4" />
                Clear filters
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Assigned To Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                <User className="w-3 h-3 inline mr-1" />
                Assigned To
              </label>
              <select
                value={assigneeFilter}
                onChange={(e) => setAssigneeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">All team members</option>
                {assignees.map((assignee) => (
                  <option key={assignee} value={assignee}>
                    {assignee}
                  </option>
                ))}
              </select>
            </div>

            {/* Project Filter */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                <FolderKanban className="w-3 h-3 inline mr-1" />
                Project
              </label>
              <select
                value={projectFilter}
                onChange={(e) => setProjectFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">All projects</option>
                {projects.map((project) => (
                  <option key={project} value={project}>
                    {project}
                  </option>
                ))}
              </select>
            </div>

            {/* Start Date Range */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                <Calendar className="w-3 h-3 inline mr-1" />
                Start Date Range
              </label>
              <div className="flex gap-2">
                <input
                  type="date"
                  value={startDateFrom}
                  onChange={(e) => setStartDateFrom(e.target.value)}
                  className="flex-1 px-2 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  title="From"
                />
                <input
                  type="date"
                  value={startDateTo}
                  onChange={(e) => setStartDateTo(e.target.value)}
                  className="flex-1 px-2 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  title="To"
                />
              </div>
            </div>

            {/* Due Date Range */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                <Calendar className="w-3 h-3 inline mr-1" />
                Due Date Range
              </label>
              <div className="flex gap-2">
                <input
                  type="date"
                  value={dueDateFrom}
                  onChange={(e) => setDueDateFrom(e.target.value)}
                  className="flex-1 px-2 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  title="From"
                />
                <input
                  type="date"
                  value={dueDateTo}
                  onChange={(e) => setDueDateTo(e.target.value)}
                  className="flex-1 px-2 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  title="To"
                />
              </div>
            </div>

            {/* Completed Date Range */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                <CheckCircle className="w-3 h-3 inline mr-1" />
                Completed Date Range
              </label>
              <div className="flex gap-2">
                <input
                  type="date"
                  value={completedDateFrom}
                  onChange={(e) => setCompletedDateFrom(e.target.value)}
                  className="flex-1 px-2 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  title="From"
                />
                <input
                  type="date"
                  value={completedDateTo}
                  onChange={(e) => setCompletedDateTo(e.target.value)}
                  className="flex-1 px-2 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  title="To"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Task Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="Total Tasks"
            value={displaySummary.total}
            icon={<CheckCircle className="w-6 h-6 text-blue-500" />}
            color="blue"
            loading={tasksLoading}
          />
          <StatCard
            title="In Progress"
            value={displaySummary.in_progress}
            icon={<Clock className="w-6 h-6 text-yellow-500" />}
            color="yellow"
            loading={tasksLoading}
          />
          <StatCard
            title="Completed"
            value={displaySummary.done}
            icon={<CheckCircle className="w-6 h-6 text-green-500" />}
            color="green"
            loading={tasksLoading}
          />
          <StatCard
            title="Overdue"
            value={displaySummary.overdue}
            icon={<AlertCircle className="w-6 h-6 text-red-500" />}
            color="red"
            loading={tasksLoading}
          />
        </div>

        {/* Task Status Breakdown */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Task Breakdown
            {hasActiveFilters && (
              <span className="ml-2 text-sm font-normal text-gray-500">(filtered)</span>
            )}
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <p className="text-3xl font-bold text-green-600">
                {tasksLoading ? "..." : displaySummary.done}
              </p>
              <p className="text-sm text-green-700 mt-1">Done</p>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-3xl font-bold text-blue-600">
                {tasksLoading ? "..." : displaySummary.in_progress}
              </p>
              <p className="text-sm text-blue-700 mt-1">In Progress</p>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <p className="text-3xl font-bold text-yellow-600">
                {tasksLoading ? "..." : displaySummary.on_hold}
              </p>
              <p className="text-sm text-yellow-700 mt-1">On Hold</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-3xl font-bold text-gray-600">
                {tasksLoading ? "..." : displaySummary.assigned}
              </p>
              <p className="text-sm text-gray-700 mt-1">Assigned</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  loading,
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  loading?: boolean;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">
            {loading ? "..." : value}
          </p>
        </div>
        {icon}
      </div>
    </div>
  );
}
