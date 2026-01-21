"use client";

import { useEffect, useState } from "react";
import {
  Plus,
  Search,
  User,
  FolderKanban,
  RefreshCw,
  Upload,
  CheckSquare,
  Square,
  Loader2,
  Sparkles,
  Repeat,
  Trash2,
} from "lucide-react";
import Header from "@/components/layout/header";
import LoadingSpinner from "@/components/common/loading-spinner";
import MarkdownEditor from "@/components/common/markdown-editor";
import TaskCard from "@/components/tasks/task-card";
import TaskCommentsPanel from "@/components/tasks/task-comments-panel";
import {
  getTasks,
  createTask,
  updateTask,
  deleteTask,
  updateTaskStatus,
  getTaskAssignees,
  getTaskProjects,
  getTaigaConfig,
  syncTasksToTaiga,
  updateTasksFromTaiga,
  generateTaskDescription,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Task, TaskStatus, TaskPriority, RecurrenceType } from "@/lib/types";
import toast from "react-hot-toast";

const statusFilters: { label: string; value: TaskStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Assigned", value: "assigned" },
  { label: "In Progress", value: "in_progress" },
  { label: "On Hold", value: "on_hold" },
  { label: "Done", value: "done" },
];

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
  const [assigneeFilter, setAssigneeFilter] = useState<string>("");
  const [assignees, setAssignees] = useState<string[]>([]);
  const [projectFilter, setProjectFilter] = useState<string>("");
  const [projects, setProjects] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [showNewTaskModal, setShowNewTaskModal] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  // Selection state for Taiga sync
  const [selectedTasks, setSelectedTasks] = useState<Set<number>>(new Set());
  const [taigaConfigured, setTaigaConfigured] = useState(false);
  const [syncingToTaiga, setSyncingToTaiga] = useState(false);
  const [updatingFromTaiga, setUpdatingFromTaiga] = useState(false);

  useEffect(() => {
    loadAssignees();
    loadProjects();
    checkTaigaConfig();
  }, []);

  useEffect(() => {
    loadTasks();
  }, [statusFilter, assigneeFilter, projectFilter, searchQuery]);

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

  const checkTaigaConfig = async () => {
    try {
      const response = await getTaigaConfig();
      if (response.status && response.data) {
        setTaigaConfigured(response.data.is_configured);
      }
    } catch (error) {
      console.error("Failed to check Taiga config", error);
    }
  };

  const toggleTaskSelection = (taskId: number) => {
    const newSelected = new Set(selectedTasks);
    if (newSelected.has(taskId)) {
      newSelected.delete(taskId);
    } else {
      newSelected.add(taskId);
    }
    setSelectedTasks(newSelected);
  };

  const selectAllTasks = () => {
    setSelectedTasks(new Set(tasks.map((t) => t.id)));
  };

  const deselectAllTasks = () => {
    setSelectedTasks(new Set());
  };

  const handleSyncToTaiga = async () => {
    if (selectedTasks.size === 0) {
      toast.error("Please select tasks to sync");
      return;
    }

    setSyncingToTaiga(true);
    try {
      const response = await syncTasksToTaiga(Array.from(selectedTasks));
      if (response.status && response.data) {
        const { synced_count, error_count, results } = response.data;
        if (synced_count > 0) {
          toast.success(`Synced ${synced_count} tasks to Taiga`);
        }
        if (error_count > 0) {
          toast.error(`${error_count} tasks failed to sync`);
        }
        // Show details
        results.forEach((r) => {
          if (r.action === "created") {
            console.log(`Created: ${r.task_title} -> Taiga #${r.taiga_id}`);
          } else if (r.action === "updated") {
            console.log(`Updated: ${r.task_title} - ${r.message}`);
          } else if (r.action === "error") {
            console.error(`Error: ${r.task_title} - ${r.message}`);
          }
        });
        setSelectedTasks(new Set());
        loadTasks();
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to sync to Taiga");
    } finally {
      setSyncingToTaiga(false);
    }
  };

  const handleUpdateFromTaiga = async () => {
    setUpdatingFromTaiga(true);
    try {
      const response = await updateTasksFromTaiga();
      if (response.status && response.data) {
        const { updated_count, results } = response.data;
        if (updated_count > 0) {
          toast.success(`Updated ${updated_count} tasks from Taiga`);
        } else {
          toast("No tasks to update from Taiga", { icon: "ℹ️" });
        }
        loadTasks();
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to update from Taiga");
    } finally {
      setUpdatingFromTaiga(false);
    }
  };

  const loadTasks = async () => {
    setLoading(true);
    try {
      const response = await getTasks({
        status: statusFilter === "all" ? undefined : statusFilter,
        assigned_to: assigneeFilter || undefined,
        project: projectFilter || undefined,
        search: searchQuery || undefined,
        limit: 50,
      });
      if (response.status && response.data) {
        setTasks(response.data.tasks);
      }
    } catch (error) {
      console.error("Failed to load tasks", error);
      toast.error("Failed to load tasks");
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (taskId: number, newStatus: TaskStatus) => {
    try {
      await updateTaskStatus(taskId, newStatus);
      toast.success("Task status updated");
      loadTasks();
    } catch (error) {
      toast.error("Failed to update task");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Tasks" />

      <div className="flex-1 p-6 overflow-auto">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
          {/* Search */}
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            {/* Taiga Sync Buttons */}
            {taigaConfigured && (
              <>
                <button
                  onClick={handleUpdateFromTaiga}
                  disabled={updatingFromTaiga}
                  className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                  title="Update all linked tasks from Taiga"
                >
                  {updatingFromTaiga ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  <span className="hidden sm:inline">Update from Taiga</span>
                </button>
                <button
                  onClick={handleSyncToTaiga}
                  disabled={syncingToTaiga || selectedTasks.size === 0}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg transition-colors",
                    selectedTasks.size > 0
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "border border-gray-300 text-gray-400 cursor-not-allowed"
                  )}
                  title={selectedTasks.size > 0 ? `Sync ${selectedTasks.size} selected tasks to Taiga` : "Select tasks to sync"}
                >
                  {syncingToTaiga ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4" />
                  )}
                  <span className="hidden sm:inline">
                    Sync to Taiga {selectedTasks.size > 0 && `(${selectedTasks.size})`}
                  </span>
                </button>
              </>
            )}

            {/* Add Task Button */}
            <button
              onClick={() => setShowNewTaskModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Task
            </button>
          </div>
        </div>

        {/* Status Filters */}
        <div className="flex items-center gap-2 mb-4">
          {statusFilters.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setStatusFilter(filter.value)}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                statusFilter === filter.value
                  ? "bg-primary-100 text-primary-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              )}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {/* Filters Row */}
        <div className="flex items-center gap-6 mb-6 flex-wrap">
          {/* Assignee Filter */}
          {assignees.length > 0 && (
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-500">Assigned to:</span>
              <select
                value={assigneeFilter}
                onChange={(e) => setAssigneeFilter(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">All team members</option>
                {assignees.map((assignee) => (
                  <option key={assignee} value={assignee}>
                    {assignee}
                  </option>
                ))}
              </select>
              {assigneeFilter && (
                <button
                  onClick={() => setAssigneeFilter("")}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear
                </button>
              )}
            </div>
          )}

          {/* Project Filter */}
          {projects.length > 0 && (
            <div className="flex items-center gap-2">
              <FolderKanban className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-500">Project:</span>
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
              {projectFilter && (
                <button
                  onClick={() => setProjectFilter("")}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear
                </button>
              )}
            </div>
          )}
        </div>

        {/* Selection Controls (when Taiga is configured) */}
        {taigaConfigured && tasks.length > 0 && (
          <div className="flex items-center gap-4 mb-4 text-sm">
            <button
              onClick={selectAllTasks}
              className="text-primary-600 hover:text-primary-700"
            >
              Select All
            </button>
            <button
              onClick={deselectAllTasks}
              className="text-gray-500 hover:text-gray-700"
            >
              Deselect All
            </button>
            {selectedTasks.size > 0 && (
              <span className="text-gray-500">
                {selectedTasks.size} task{selectedTasks.size > 1 ? "s" : ""} selected
              </span>
            )}
          </div>
        )}

        {/* Task List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No tasks found</p>
            <button
              onClick={() => setShowNewTaskModal(true)}
              className="mt-4 text-primary-600 hover:text-primary-700 font-medium"
            >
              Create your first task
            </button>
          </div>
        ) : (
          <div className="grid gap-4">
            {tasks.map((task) => (
              <div key={task.id} className="flex items-start gap-3">
                {/* Selection Checkbox (when Taiga configured) */}
                {taigaConfigured && (
                  <button
                    onClick={() => toggleTaskSelection(task.id)}
                    className="mt-4 flex-shrink-0"
                  >
                    {selectedTasks.has(task.id) ? (
                      <CheckSquare className="w-5 h-5 text-primary-600" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-400 hover:text-gray-600" />
                    )}
                  </button>
                )}
                <div className="flex-1">
                  <TaskCard task={task} onClick={() => setEditingTask(task)} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Task Modal */}
      {showNewTaskModal && (
        <NewTaskModal
          onClose={() => setShowNewTaskModal(false)}
          onCreated={() => {
            setShowNewTaskModal(false);
            loadTasks();
          }}
        />
      )}

      {/* Edit Task Modal */}
      {editingTask && (
        <EditTaskModal
          task={editingTask}
          onClose={() => setEditingTask(null)}
          onUpdated={() => {
            setEditingTask(null);
            loadTasks();
          }}
        />
      )}
    </div>
  );
}

function NewTaskModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<TaskStatus>("assigned");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [project, setProject] = useState("");
  const [startDate, setStartDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurrenceType, setRecurrenceType] = useState<RecurrenceType>("weekly");
  const [recurrenceEndDate, setRecurrenceEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [generatingDescription, setGeneratingDescription] = useState(false);
  const [suggestedTitle, setSuggestedTitle] = useState<string | null>(null);

  const handleGenerateDescription = async () => {
    if (!title.trim()) {
      toast.error("Please enter a task title first");
      return;
    }

    setGeneratingDescription(true);
    setSuggestedTitle(null);
    try {
      const response = await generateTaskDescription({
        title: title.trim(),
        current_description: description.trim() || undefined,
        project: project.trim() || undefined,
      });
      if (response.status && response.data) {
        setDescription(response.data.description);
        if (response.data.suggested_title) {
          setSuggestedTitle(response.data.suggested_title);
        }
        toast.success("Suggestion generated");
      }
    } catch (error) {
      toast.error("Failed to generate suggestion");
    } finally {
      setGeneratingDescription(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setLoading(true);
    try {
      await createTask({
        title: title.trim(),
        description: description.trim() || undefined,
        status,
        priority,
        project: project.trim() || undefined,
        start_date: startDate || undefined,
        due_date: dueDate || undefined,
        assigned_to: assignedTo.trim() || undefined,
        is_recurring: isRecurring,
        recurrence_type: isRecurring ? recurrenceType : "none",
        recurrence_end_date: isRecurring && recurrenceEndDate ? recurrenceEndDate : undefined,
      });
      toast.success("Task created");
      onCreated();
    } catch (error) {
      toast.error("Failed to create task");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-md mx-4 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">New Task</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="Task title"
              required
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <button
                type="button"
                onClick={handleGenerateDescription}
                disabled={generatingDescription || !title.trim()}
                className="flex items-center gap-1 px-2 py-1 text-xs text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                title="Generate description with AI"
              >
                {generatingDescription ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Sparkles className="w-3 h-3" />
                )}
                AI Suggest
              </button>
            </div>
            {suggestedTitle && (
              <div className="mb-2 p-2 bg-primary-50 border border-primary-200 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="w-3 h-3 text-primary-600" />
                  <span className="text-xs font-medium text-primary-700">Suggested Title</span>
                </div>
                <p className="text-sm text-primary-800">{suggestedTitle}</p>
                <button
                  type="button"
                  onClick={() => {
                    setTitle(suggestedTitle);
                    setSuggestedTitle(null);
                    toast.success("Title updated");
                  }}
                  className="mt-1 text-xs text-primary-600 hover:text-primary-700 hover:underline"
                >
                  Use this title
                </button>
              </div>
            )}
            <MarkdownEditor
              value={description}
              onChange={setDescription}
              placeholder="Task description (supports Markdown)"
              minHeight={120}
              maxHeight={200}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assigned To
              </label>
              <input
                type="text"
                value={assignedTo}
                onChange={(e) => setAssignedTo(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="Team member"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project
              </label>
              <input
                type="text"
                value={project}
                onChange={(e) => setProject(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="Project name"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as TaskStatus)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="assigned">Assigned</option>
                <option value="in_progress">In Progress</option>
                <option value="on_hold">On Hold</option>
                <option value="done">Done</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Due Date
              </label>
              <input
                type="datetime-local"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          {/* Recurrence */}
          <div className="border-t pt-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isRecurring}
                onChange={(e) => setIsRecurring(e.target.checked)}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <Repeat className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Recurring task</span>
            </label>

            {isRecurring && (
              <div className="mt-3 grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Repeat
                  </label>
                  <select
                    value={recurrenceType}
                    onChange={(e) => setRecurrenceType(e.target.value as RecurrenceType)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="biweekly">Every 2 Weeks</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    End Date (optional)
                  </label>
                  <input
                    type="date"
                    value={recurrenceEndDate}
                    onChange={(e) => setRecurrenceEndDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create Task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditTaskModal({
  task,
  onClose,
  onUpdated,
}: {
  task: Task;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description || "");
  const [status, setStatus] = useState<TaskStatus>(task.status);
  const [priority, setPriority] = useState<TaskPriority>(task.priority);
  const [project, setProject] = useState(task.project || "");
  const [startDate, setStartDate] = useState(
    task.start_date ? new Date(task.start_date).toISOString().slice(0, 16) : ""
  );
  const [dueDate, setDueDate] = useState(
    task.due_date ? new Date(task.due_date).toISOString().slice(0, 16) : ""
  );
  const [assignedTo, setAssignedTo] = useState(task.assigned_to || "");
  const [isRecurring, setIsRecurring] = useState(task.is_recurring || false);
  const [recurrenceType, setRecurrenceType] = useState<RecurrenceType>(
    task.recurrence_type || "weekly"
  );
  const [recurrenceEndDate, setRecurrenceEndDate] = useState(
    task.recurrence_end_date ? new Date(task.recurrence_end_date).toISOString().slice(0, 10) : ""
  );
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [generatingDescription, setGeneratingDescription] = useState(false);
  const [suggestedTitle, setSuggestedTitle] = useState<string | null>(null);

  const handleGenerateDescription = async () => {
    if (!title.trim()) {
      toast.error("Please enter a task title first");
      return;
    }

    setGeneratingDescription(true);
    setSuggestedTitle(null);
    try {
      const response = await generateTaskDescription({
        title: title.trim(),
        current_description: description.trim() || undefined,
        project: project.trim() || undefined,
      });
      if (response.status && response.data) {
        setDescription(response.data.description);
        if (response.data.suggested_title) {
          setSuggestedTitle(response.data.suggested_title);
        }
        toast.success("Suggestion generated");
      }
    } catch (error) {
      toast.error("Failed to generate suggestion");
    } finally {
      setGeneratingDescription(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteTask(task.id);
      toast.success("Task deleted");
      onUpdated();
    } catch (error) {
      toast.error("Failed to delete task");
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setLoading(true);
    try {
      await updateTask(task.id, {
        title: title.trim(),
        description: description.trim() || undefined,
        status,
        priority,
        project: project.trim() || undefined,
        start_date: startDate || undefined,
        due_date: dueDate || undefined,
        assigned_to: assignedTo.trim() || undefined,
        is_recurring: isRecurring,
        recurrence_type: isRecurring ? recurrenceType : "none",
        recurrence_end_date: isRecurring && recurrenceEndDate ? recurrenceEndDate : undefined,
      });
      toast.success("Task updated");
      onUpdated();
    } catch (error) {
      toast.error("Failed to update task");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-2xl mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Edit Task</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="Task title"
              required
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <button
                type="button"
                onClick={handleGenerateDescription}
                disabled={generatingDescription || !title.trim()}
                className="flex items-center gap-1 px-2 py-1 text-xs text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                title="Generate description with AI"
              >
                {generatingDescription ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Sparkles className="w-3 h-3" />
                )}
                AI Suggest
              </button>
            </div>
            {suggestedTitle && (
              <div className="mb-2 p-2 bg-primary-50 border border-primary-200 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="w-3 h-3 text-primary-600" />
                  <span className="text-xs font-medium text-primary-700">Suggested Title</span>
                </div>
                <p className="text-sm text-primary-800">{suggestedTitle}</p>
                <button
                  type="button"
                  onClick={() => {
                    setTitle(suggestedTitle);
                    setSuggestedTitle(null);
                    toast.success("Title updated");
                  }}
                  className="mt-1 text-xs text-primary-600 hover:text-primary-700 hover:underline"
                >
                  Use this title
                </button>
              </div>
            )}
            <MarkdownEditor
              value={description}
              onChange={setDescription}
              placeholder="Task description (supports Markdown)"
              minHeight={120}
              maxHeight={200}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assigned To
              </label>
              <input
                type="text"
                value={assignedTo}
                onChange={(e) => setAssignedTo(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="Team member"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project
              </label>
              <input
                type="text"
                value={project}
                onChange={(e) => setProject(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="Project name"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as TaskStatus)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="assigned">Assigned</option>
                <option value="in_progress">In Progress</option>
                <option value="on_hold">On Hold</option>
                <option value="done">Done</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Due Date
              </label>
              <input
                type="datetime-local"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          {/* Recurrence - only show if not a generated instance */}
          {!task.parent_task_id && (
            <div className="border-t pt-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isRecurring}
                  onChange={(e) => setIsRecurring(e.target.checked)}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <Repeat className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700">Recurring task</span>
              </label>

              {isRecurring && (
                <div className="mt-3 grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Repeat
                    </label>
                    <select
                      value={recurrenceType}
                      onChange={(e) => setRecurrenceType(e.target.value as RecurrenceType)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="biweekly">Every 2 Weeks</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      End Date (optional)
                    </label>
                    <input
                      type="date"
                      value={recurrenceEndDate}
                      onChange={(e) => setRecurrenceEndDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Show parent task info if this is a generated instance */}
          {task.parent_task_id && (
            <div className="border-t pt-4">
              <p className="text-sm text-gray-500 flex items-center gap-2">
                <Repeat className="w-4 h-4" />
                This is an instance of a recurring task
              </p>
            </div>
          )}

          <div className="flex justify-between gap-3 pt-4">
            <button
              type="button"
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2 px-4 py-2 text-red-600 border border-red-300 rounded-lg hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !title.trim()}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {loading ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </form>

        {/* Delete Confirmation Dialog */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
            <div className="bg-white rounded-lg p-6 max-w-sm mx-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete Task</h3>
              <p className="text-gray-600 mb-4">
                Are you sure you want to delete &quot;{task.title}&quot;? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                >
                  {deleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Task Comments Section */}
        <TaskCommentsPanel task={task} onTaskUpdated={onUpdated} />
      </div>
    </div>
  );
}
