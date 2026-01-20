"use client";

import { useEffect, useState } from "react";
import {
  Sparkles,
  Mail,
  Calendar,
  CheckSquare,
  Square,
  Plus,
  Loader2,
  AlertCircle,
  FileText,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import Header from "@/components/layout/header";
import LoadingSpinner from "@/components/common/loading-spinner";
import {
  getEmailSuggestions,
  addSuggestedTasks,
  getTaskProjects,
  type TaskSuggestion,
  type EmailSummaryResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";

function getWeekDateRange(): { start: string; end: string } {
  const today = new Date();
  const dayOfWeek = today.getDay();
  const monday = new Date(today);
  monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  monday.setHours(0, 0, 0, 0);

  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  sunday.setHours(23, 59, 59, 999);

  return {
    start: monday.toISOString().split("T")[0],
    end: sunday.toISOString().split("T")[0],
  };
}

function formatDateForDisplay(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export default function AIAssistantPage() {
  const [loading, setLoading] = useState(false);
  const [addingTasks, setAddingTasks] = useState(false);
  const [data, setData] = useState<EmailSummaryResponse | null>(null);
  const [selectedTasks, setSelectedTasks] = useState<Set<number>>(new Set());
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [showSummary, setShowSummary] = useState(true);

  // Date range state - default to current week
  const defaultRange = getWeekDateRange();
  const [startDate, setStartDate] = useState(defaultRange.start);
  const [endDate, setEndDate] = useState(defaultRange.end);

  useEffect(() => {
    loadProjects();
  }, []);

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

  const generateSuggestions = async () => {
    setLoading(true);
    setData(null);
    setSelectedTasks(new Set());

    try {
      const response = await getEmailSuggestions({
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate + "T23:59:59").toISOString(),
      });

      if (response.status && response.data) {
        setData(response.data);
        if (response.data.email_count === 0) {
          toast("No emails found in this date range", { icon: "📭" });
        }
      }
    } catch (error: any) {
      console.error("Failed to get suggestions", error);
      toast.error(error.response?.data?.detail || "Failed to generate suggestions");
    } finally {
      setLoading(false);
    }
  };

  const toggleTask = (index: number) => {
    const newSelected = new Set(selectedTasks);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedTasks(newSelected);
  };

  const selectAll = () => {
    if (data?.task_suggestions) {
      setSelectedTasks(new Set(data.task_suggestions.map((_, i) => i)));
    }
  };

  const deselectAll = () => {
    setSelectedTasks(new Set());
  };

  const addSelectedTasks = async () => {
    if (!data?.task_suggestions || selectedTasks.size === 0) return;

    setAddingTasks(true);
    try {
      const tasksToAdd = Array.from(selectedTasks).map(
        (i) => data.task_suggestions[i]
      );

      const response = await addSuggestedTasks({
        tasks: tasksToAdd,
        project: selectedProject || undefined,
      });

      if (response.status && response.data) {
        toast.success(`Added ${response.data.added_count} tasks`);
        setSelectedTasks(new Set());
        // Refresh projects list in case new project was created
        loadProjects();
      }
    } catch (error: any) {
      console.error("Failed to add tasks", error);
      toast.error(error.response?.data?.detail || "Failed to add tasks");
    } finally {
      setAddingTasks(false);
    }
  };

  const setThisWeek = () => {
    const range = getWeekDateRange();
    setStartDate(range.start);
    setEndDate(range.end);
  };

  const setLastWeek = () => {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const lastMonday = new Date(today);
    lastMonday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1) - 7);
    lastMonday.setHours(0, 0, 0, 0);

    const lastSunday = new Date(lastMonday);
    lastSunday.setDate(lastMonday.getDate() + 6);

    setStartDate(lastMonday.toISOString().split("T")[0]);
    setEndDate(lastSunday.toISOString().split("T")[0]);
  };

  const setLast7Days = () => {
    const today = new Date();
    const weekAgo = new Date(today);
    weekAgo.setDate(today.getDate() - 7);

    setStartDate(weekAgo.toISOString().split("T")[0]);
    setEndDate(today.toISOString().split("T")[0]);
  };

  const priorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "urgent":
        return "bg-red-100 text-red-700";
      case "high":
        return "bg-orange-100 text-orange-700";
      case "medium":
        return "bg-yellow-100 text-yellow-700";
      case "low":
        return "bg-green-100 text-green-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="AI Assistant" />

      <div className="flex-1 p-6 overflow-auto">
        {/* Intro Section */}
        <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg border border-primary-200 p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-primary-100 rounded-lg">
              <Sparkles className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-1">
                Email Task Suggestions
              </h2>
              <p className="text-gray-600">
                AI analyzes your emails to suggest actionable tasks. Select a date
                range and click &quot;Generate Suggestions&quot; to get started.
              </p>
            </div>
          </div>
        </div>

        {/* Date Range Selection */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            Select Date Range
          </h3>

          <div className="flex flex-wrap items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">From:</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">To:</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            <button
              onClick={setThisWeek}
              className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              This Week
            </button>
            <button
              onClick={setLastWeek}
              className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Last Week
            </button>
            <button
              onClick={setLast7Days}
              className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Last 7 Days
            </button>
          </div>

          <button
            onClick={generateSuggestions}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing Emails...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Generate Suggestions
              </>
            )}
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-gray-500">
              AI is analyzing your emails and extracting tasks...
            </p>
          </div>
        )}

        {/* Results */}
        {data && !loading && (
          <div className="space-y-6">
            {/* Email Summary */}
            <div className="bg-white rounded-lg border border-gray-200">
              <button
                onClick={() => setShowSummary(!showSummary)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Mail className="w-5 h-5 text-gray-500" />
                  <span className="font-semibold text-gray-900">
                    Email Summary
                  </span>
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-sm rounded-full">
                    {data.email_count} emails
                  </span>
                  <span className="text-sm text-gray-500">
                    {formatDateForDisplay(data.date_range.start)} -{" "}
                    {formatDateForDisplay(data.date_range.end)}
                  </span>
                </div>
                {showSummary ? (
                  <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
              </button>
              {showSummary && (
                <div className="px-4 pb-4 border-t border-gray-100">
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-start gap-2">
                      <FileText className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                      <p className="text-gray-700 whitespace-pre-wrap">
                        {data.summary}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Task Suggestions */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <CheckSquare className="w-5 h-5 text-gray-500" />
                  Task Suggestions
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 text-sm rounded-full">
                    {data.task_suggestions.length} found
                  </span>
                </h3>
                {data.task_suggestions.length > 0 && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={selectAll}
                      className="text-sm text-primary-600 hover:text-primary-700"
                    >
                      Select All
                    </button>
                    <span className="text-gray-300">|</span>
                    <button
                      onClick={deselectAll}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      Deselect All
                    </button>
                  </div>
                )}
              </div>

              {data.task_suggestions.length === 0 ? (
                <div className="text-center py-8">
                  <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">
                    No actionable tasks found in your emails.
                  </p>
                </div>
              ) : (
                <>
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {data.task_suggestions.map((task, index) => (
                      <div
                        key={index}
                        onClick={() => toggleTask(index)}
                        className={cn(
                          "p-4 border rounded-lg cursor-pointer transition-all",
                          selectedTasks.has(index)
                            ? "border-primary-500 bg-primary-50"
                            : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <div className="pt-0.5">
                            {selectedTasks.has(index) ? (
                              <CheckSquare className="w-5 h-5 text-primary-600" />
                            ) : (
                              <Square className="w-5 h-5 text-gray-400" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-gray-900">
                                {task.title}
                              </span>
                              <span
                                className={cn(
                                  "px-2 py-0.5 text-xs rounded-full",
                                  priorityColor(task.priority)
                                )}
                              >
                                {task.priority}
                              </span>
                            </div>
                            {task.description && (
                              <p className="text-sm text-gray-600 mb-2">
                                {task.description}
                              </p>
                            )}
                            <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                              {task.source_email_subject && (
                                <span className="flex items-center gap-1">
                                  <Mail className="w-3 h-3" />
                                  {task.source_email_subject.length > 40
                                    ? task.source_email_subject.substring(0, 40) +
                                      "..."
                                    : task.source_email_subject}
                                </span>
                              )}
                              {task.due_date_hint &&
                                task.due_date_hint.toLowerCase() !== "none" && (
                                  <span className="flex items-center gap-1 text-orange-600">
                                    <Calendar className="w-3 h-3" />
                                    {task.due_date_hint}
                                  </span>
                                )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Add Tasks Section */}
                  {selectedTasks.size > 0 && (
                    <div className="mt-6 pt-4 border-t border-gray-200">
                      <div className="flex items-center gap-4 flex-wrap">
                        <div className="flex items-center gap-2">
                          <label className="text-sm text-gray-600">
                            Add to project:
                          </label>
                          <select
                            value={selectedProject}
                            onChange={(e) => setSelectedProject(e.target.value)}
                            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                          >
                            <option value="">No project</option>
                            {projects.map((project) => (
                              <option key={project} value={project}>
                                {project}
                              </option>
                            ))}
                          </select>
                          <span className="text-sm text-gray-400">or</span>
                          <input
                            type="text"
                            placeholder="New project name"
                            value={
                              projects.includes(selectedProject)
                                ? ""
                                : selectedProject
                            }
                            onChange={(e) => setSelectedProject(e.target.value)}
                            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 w-40"
                          />
                        </div>
                        <button
                          onClick={addSelectedTasks}
                          disabled={addingTasks}
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                        >
                          {addingTasks ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              Adding...
                            </>
                          ) : (
                            <>
                              <Plus className="w-4 h-4" />
                              Add {selectedTasks.size} Task
                              {selectedTasks.size > 1 ? "s" : ""}
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
