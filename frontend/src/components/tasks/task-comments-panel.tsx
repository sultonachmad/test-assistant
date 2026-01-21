"use client";

import { useState, useEffect } from "react";
import {
  MessageCircle,
  HelpCircle,
  RefreshCw,
  Lightbulb,
  CheckSquare,
  Sparkles,
  Loader2,
  Plus,
  Edit2,
  Trash2,
  ChevronDown,
  ChevronUp,
  Calendar,
  Clock,
  ListTodo,
  X,
  Check,
} from "lucide-react";
import {
  getTaskComments,
  createTaskComment,
  updateTaskComment,
  deleteTaskComment,
  generateAIComment,
  generateAndSaveAIComment,
  suggestTasksFromComments,
  updateTaskFromSolution,
  createTask,
} from "@/lib/api";
import type { Task, TaskComment, CommentType, TaskSuggestion } from "@/lib/types";
import MarkdownEditor from "@/components/common/markdown-editor";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";

const COMMENT_TYPES: { type: CommentType; label: string; icon: React.ReactNode; color: string }[] = [
  { type: "ask", label: "Ask", icon: <HelpCircle className="w-4 h-4" />, color: "text-blue-600 bg-blue-50 border-blue-200" },
  { type: "update", label: "Update", icon: <RefreshCw className="w-4 h-4" />, color: "text-green-600 bg-green-50 border-green-200" },
  { type: "solution", label: "Solution", icon: <Lightbulb className="w-4 h-4" />, color: "text-amber-600 bg-amber-50 border-amber-200" },
  { type: "test_case", label: "Test Case", icon: <CheckSquare className="w-4 h-4" />, color: "text-purple-600 bg-purple-50 border-purple-200" },
];

interface TaskCommentsPanelProps {
  task: Task;
  onTaskUpdated?: () => void;
}

export default function TaskCommentsPanel({ task, onTaskUpdated }: TaskCommentsPanelProps) {
  const [comments, setComments] = useState<TaskComment[]>([]);
  const [counts, setCounts] = useState<Record<CommentType, number>>({} as Record<CommentType, number>);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<CommentType | "all">("all");

  // New comment form
  const [showNewForm, setShowNewForm] = useState(false);
  const [newCommentType, setNewCommentType] = useState<CommentType>("update");
  const [newContent, setNewContent] = useState("");
  const [creating, setCreating] = useState(false);

  // Edit mode
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");

  // AI generation
  const [generatingAI, setGeneratingAI] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [selectedForContext, setSelectedForContext] = useState<Set<number>>(new Set());
  const [showAIPanel, setShowAIPanel] = useState(false);

  // Solution dates editing
  const [editingSolutionId, setEditingSolutionId] = useState<number | null>(null);
  const [solutionStartDate, setSolutionStartDate] = useState("");
  const [solutionDueDate, setSolutionDueDate] = useState("");
  const [solutionEstDays, setSolutionEstDays] = useState(1);

  // Task suggestions
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<TaskSuggestion[]>([]);
  const [generatingSuggestions, setGeneratingSuggestions] = useState(false);

  // Create task from suggestion modal
  const [showCreateTaskModal, setShowCreateTaskModal] = useState(false);
  const [creatingTask, setCreatingTask] = useState(false);
  const [newTaskFromSuggestion, setNewTaskFromSuggestion] = useState({
    title: "",
    description: "",
    priority: "medium" as "low" | "medium" | "high" | "urgent",
    project: "",
    due_date: "",
    status: "assigned" as "done" | "in_progress" | "on_hold" | "assigned",
  });

  useEffect(() => {
    loadComments();
  }, [task.id]);

  const loadComments = async () => {
    setLoading(true);
    try {
      const response = await getTaskComments(task.id);
      if (response.status && response.data) {
        setComments(response.data.comments);
        setCounts(response.data.counts);
      }
    } catch (error) {
      console.error("Failed to load comments", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateComment = async () => {
    if (!newContent.trim()) return;

    setCreating(true);
    try {
      const response = await createTaskComment({
        task_id: task.id,
        comment_type: newCommentType,
        content: newContent.trim(),
      });
      if (response.status) {
        toast.success("Comment added");
        setNewContent("");
        setShowNewForm(false);
        loadComments();
      }
    } catch (error) {
      toast.error("Failed to add comment");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateComment = async (commentId: number) => {
    if (!editContent.trim()) return;

    try {
      const response = await updateTaskComment(commentId, { content: editContent.trim() });
      if (response.status) {
        toast.success("Comment updated");
        setEditingId(null);
        loadComments();
      }
    } catch (error) {
      toast.error("Failed to update comment");
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!confirm("Delete this comment?")) return;

    try {
      const response = await deleteTaskComment(commentId);
      if (response.status) {
        toast.success("Comment deleted");
        loadComments();
      }
    } catch (error) {
      toast.error("Failed to delete comment");
    }
  };

  const handleGenerateAI = async (type: CommentType, save: boolean = false) => {
    setGeneratingAI(true);
    try {
      const data = {
        task_id: task.id,
        comment_type: type,
        prompt: aiPrompt.trim() || undefined,
        selected_comment_ids: selectedForContext.size > 0 ? Array.from(selectedForContext) : undefined,
      };

      if (save) {
        const response = await generateAndSaveAIComment(data);
        if (response.status) {
          toast.success("AI comment added");
          setAiPrompt("");
          setSelectedForContext(new Set());
          setShowAIPanel(false);
          loadComments();
        }
      } else {
        const response = await generateAIComment(data);
        if (response.status && response.data) {
          setNewCommentType(type);
          setNewContent(response.data.content);
          setShowNewForm(true);
          setShowAIPanel(false);

          // If solution type, set dates
          if (type === "solution" && response.data.estimated_days) {
            // Will be handled when saving the comment
          }
        }
      }
    } catch (error) {
      toast.error("Failed to generate AI comment");
    } finally {
      setGeneratingAI(false);
    }
  };

  const handleGenerateTaskSuggestions = async () => {
    if (selectedForContext.size === 0) {
      toast.error("Select at least one comment for context");
      return;
    }

    setGeneratingSuggestions(true);
    try {
      const response = await suggestTasksFromComments({
        task_id: task.id,
        selected_comment_ids: Array.from(selectedForContext),
        prompt: aiPrompt.trim() || undefined,
      });
      if (response.status && response.data) {
        setSuggestions(response.data.suggestions);
        setShowSuggestions(true);
      }
    } catch (error) {
      toast.error("Failed to generate task suggestions");
    } finally {
      setGeneratingSuggestions(false);
    }
  };

  const handleOpenCreateTaskModal = (suggestion: TaskSuggestion) => {
    // Calculate due date if estimated_days is available
    let dueDate = "";
    if (suggestion.estimated_days) {
      const startDate = task.start_date ? new Date(task.start_date) : new Date();
      startDate.setDate(startDate.getDate() + suggestion.estimated_days);
      dueDate = startDate.toISOString().split("T")[0];
    }

    setNewTaskFromSuggestion({
      title: suggestion.title,
      description: suggestion.description,
      priority: suggestion.priority,
      project: task.project || "",
      due_date: dueDate,
      status: "assigned",
    });
    setShowCreateTaskModal(true);
  };

  const handleCreateTaskFromSuggestion = async () => {
    if (!newTaskFromSuggestion.title.trim()) {
      toast.error("Title is required");
      return;
    }

    setCreatingTask(true);
    try {
      await createTask({
        title: newTaskFromSuggestion.title,
        description: newTaskFromSuggestion.description,
        priority: newTaskFromSuggestion.priority,
        project: newTaskFromSuggestion.project || undefined,
        due_date: newTaskFromSuggestion.due_date || undefined,
        status: newTaskFromSuggestion.status,
      });
      toast.success("Task created");
      setSuggestions(suggestions.filter((s) => s.title !== newTaskFromSuggestion.title));
      setShowCreateTaskModal(false);
    } catch (error) {
      toast.error("Failed to create task");
    } finally {
      setCreatingTask(false);
    }
  };

  const handleUpdateTaskFromSolution = async (comment: TaskComment) => {
    try {
      const response = await updateTaskFromSolution({
        comment_id: comment.id,
        start_date: solutionStartDate,
        due_date: solutionDueDate,
      });
      if (response.status) {
        toast.success("Task dates updated");
        setEditingSolutionId(null);
        onTaskUpdated?.();
      }
    } catch (error) {
      toast.error("Failed to update task");
    }
  };

  const toggleContextSelection = (commentId: number) => {
    const newSet = new Set(selectedForContext);
    if (newSet.has(commentId)) {
      newSet.delete(commentId);
    } else {
      newSet.add(commentId);
    }
    setSelectedForContext(newSet);
  };

  const filteredComments = activeTab === "all"
    ? comments
    : comments.filter((c) => c.comment_type === activeTab);

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString();
  };

  const getTypeConfig = (type: CommentType) => {
    return COMMENT_TYPES.find((t) => t.type === type) || COMMENT_TYPES[1];
  };

  return (
    <div className="border-t pt-4 mt-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 flex items-center gap-2">
          <MessageCircle className="w-5 h-5" />
          Comments
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAIPanel(!showAIPanel)}
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg transition-colors",
              showAIPanel
                ? "bg-primary-100 text-primary-700"
                : "border border-gray-300 hover:bg-gray-50"
            )}
          >
            <Sparkles className="w-4 h-4" />
            AI Assist
          </button>
          <button
            onClick={() => {
              setShowNewForm(!showNewForm);
              setShowAIPanel(false);
            }}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>
      </div>

      {/* AI Panel */}
      {showAIPanel && (
        <div className="mb-4 p-4 bg-gradient-to-r from-primary-50 to-purple-50 border border-primary-200 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-primary-600" />
            <span className="font-medium text-primary-800">AI Comment Assistant</span>
          </div>

          <div className="mb-3">
            <label className="block text-sm text-gray-700 mb-1">
              Optional prompt (describe what you need)
            </label>
            <input
              type="text"
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="e.g., Focus on performance aspects..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>

          {comments.length > 0 && (
            <div className="mb-3">
              <label className="block text-sm text-gray-700 mb-1">
                Select comments for context ({selectedForContext.size} selected)
              </label>
              <div className="max-h-32 overflow-y-auto border border-gray-200 rounded-lg bg-white">
                {comments.map((comment) => (
                  <label
                    key={comment.id}
                    className="flex items-start gap-2 p-2 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedForContext.has(comment.id)}
                      onChange={() => toggleContextSelection(comment.id)}
                      className="mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <span className={cn("text-xs px-1.5 py-0.5 rounded", getTypeConfig(comment.comment_type).color)}>
                        {getTypeConfig(comment.comment_type).label}
                      </span>
                      <p className="text-sm text-gray-600 truncate mt-1">{comment.content.slice(0, 80)}...</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {COMMENT_TYPES.map((type) => (
              <button
                key={type.type}
                onClick={() => handleGenerateAI(type.type, true)}
                disabled={generatingAI}
                className={cn(
                  "flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg transition-colors",
                  type.color,
                  "hover:opacity-80 disabled:opacity-50"
                )}
              >
                {generatingAI ? <Loader2 className="w-4 h-4 animate-spin" /> : type.icon}
                Generate {type.label}
              </button>
            ))}
          </div>

          {selectedForContext.size > 0 && (
            <div className="mt-3 pt-3 border-t border-primary-200">
              <button
                onClick={handleGenerateTaskSuggestions}
                disabled={generatingSuggestions}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {generatingSuggestions ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ListTodo className="w-4 h-4" />
                )}
                Suggest Tasks from Selected Comments
              </button>
            </div>
          )}
        </div>
      )}

      {/* Task Suggestions Modal */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="mb-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-medium text-purple-800 flex items-center gap-2">
              <ListTodo className="w-5 h-5" />
              Suggested Tasks ({suggestions.length})
            </h4>
            <button onClick={() => setShowSuggestions(false)} className="text-purple-600 hover:text-purple-800">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="space-y-3">
            {suggestions.map((suggestion, idx) => (
              <div key={idx} className="p-3 bg-white border border-purple-100 rounded-lg">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <h5 className="font-medium text-gray-900">{suggestion.title}</h5>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">{suggestion.description}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                      <span className="px-2 py-0.5 bg-gray-100 rounded">{suggestion.priority}</span>
                      {suggestion.estimated_days && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {suggestion.estimated_days} days
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleOpenCreateTaskModal(suggestion)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                  >
                    <Plus className="w-4 h-4" />
                    Create
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* New Comment Form */}
      {showNewForm && (
        <div className="mb-4 p-4 border border-gray-200 rounded-lg bg-gray-50">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm font-medium text-gray-700">Type:</span>
            <div className="flex gap-1">
              {COMMENT_TYPES.map((type) => (
                <button
                  key={type.type}
                  onClick={() => setNewCommentType(type.type)}
                  className={cn(
                    "flex items-center gap-1 px-2 py-1 text-xs rounded border transition-colors",
                    newCommentType === type.type ? type.color : "border-gray-300 text-gray-500 hover:bg-gray-100"
                  )}
                >
                  {type.icon}
                  {type.label}
                </button>
              ))}
            </div>
          </div>

          <MarkdownEditor
            value={newContent}
            onChange={setNewContent}
            placeholder="Write your comment in Markdown..."
            minHeight={100}
            maxHeight={200}
          />

          <div className="flex justify-end gap-2 mt-3">
            <button
              onClick={() => {
                setShowNewForm(false);
                setNewContent("");
              }}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              onClick={handleCreateComment}
              disabled={creating || !newContent.trim()}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Add Comment
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-4 border-b">
        <button
          onClick={() => setActiveTab("all")}
          className={cn(
            "px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
            activeTab === "all"
              ? "border-primary-600 text-primary-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          )}
        >
          All ({comments.length})
        </button>
        {COMMENT_TYPES.map((type) => (
          <button
            key={type.type}
            onClick={() => setActiveTab(type.type)}
            className={cn(
              "flex items-center gap-1 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              activeTab === type.type
                ? "border-primary-600 text-primary-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            {type.icon}
            {type.label} ({counts[type.type] || 0})
          </button>
        ))}
      </div>

      {/* Comments List */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : filteredComments.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No comments yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredComments.map((comment) => {
            const typeConfig = getTypeConfig(comment.comment_type);
            const isEditing = editingId === comment.id;
            const isEditingSolution = editingSolutionId === comment.id;

            return (
              <div
                key={comment.id}
                className={cn("p-3 border rounded-lg", typeConfig.color.replace("text-", "border-").split(" ")[0])}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className={cn("flex items-center gap-1 px-2 py-0.5 text-xs rounded", typeConfig.color)}>
                      {typeConfig.icon}
                      {typeConfig.label}
                    </span>
                    {comment.is_ai_generated && (
                      <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">
                        <Sparkles className="w-3 h-3" />
                        AI
                      </span>
                    )}
                    <span className="text-xs text-gray-500">
                      {new Date(comment.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    {!isEditing && (
                      <>
                        <button
                          onClick={() => {
                            setEditingId(comment.id);
                            setEditContent(comment.content);
                          }}
                          className="p-1 text-gray-400 hover:text-gray-600"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteComment(comment.id)}
                          className="p-1 text-gray-400 hover:text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {isEditing ? (
                  <div>
                    <MarkdownEditor
                      value={editContent}
                      onChange={setEditContent}
                      minHeight={80}
                      maxHeight={150}
                    />
                    <div className="flex justify-end gap-2 mt-2">
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-100"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleUpdateComment(comment.id)}
                        className="px-2 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="prose prose-sm max-w-none text-gray-700">
                    <div dangerouslySetInnerHTML={{ __html: comment.content.replace(/\n/g, '<br>') }} />
                  </div>
                )}

                {/* Solution type: show estimated days and dates */}
                {comment.comment_type === "solution" && comment.estimated_days && (
                  <div className="mt-3 pt-3 border-t border-amber-200">
                    {isEditingSolution ? (
                      <div className="space-y-2">
                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <label className="block text-xs text-gray-600 mb-1">Start Date</label>
                            <input
                              type="date"
                              value={solutionStartDate}
                              onChange={(e) => {
                                setSolutionStartDate(e.target.value);
                                if (e.target.value && solutionEstDays) {
                                  const start = new Date(e.target.value);
                                  start.setDate(start.getDate() + solutionEstDays + 1);
                                  setSolutionDueDate(start.toISOString().split("T")[0]);
                                }
                              }}
                              className="w-full px-2 py-1 text-sm border rounded"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-600 mb-1">Est. Days</label>
                            <input
                              type="number"
                              min="1"
                              value={solutionEstDays}
                              onChange={(e) => {
                                const days = parseInt(e.target.value) || 1;
                                setSolutionEstDays(days);
                                if (solutionStartDate) {
                                  const start = new Date(solutionStartDate);
                                  start.setDate(start.getDate() + days + 1);
                                  setSolutionDueDate(start.toISOString().split("T")[0]);
                                }
                              }}
                              className="w-full px-2 py-1 text-sm border rounded"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-600 mb-1">Due Date</label>
                            <input
                              type="date"
                              value={solutionDueDate}
                              onChange={(e) => setSolutionDueDate(e.target.value)}
                              className="w-full px-2 py-1 text-sm border rounded"
                            />
                          </div>
                        </div>
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setEditingSolutionId(null)}
                            className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-100"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleUpdateTaskFromSolution(comment)}
                            className="flex items-center gap-1 px-2 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700"
                          >
                            <Check className="w-3 h-3" />
                            Update Task
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 text-sm">
                          <span className="flex items-center gap-1 text-amber-700">
                            <Clock className="w-4 h-4" />
                            {comment.estimated_days} days
                          </span>
                          {comment.suggested_start_date && (
                            <span className="flex items-center gap-1 text-gray-600">
                              <Calendar className="w-4 h-4" />
                              {formatDate(comment.suggested_start_date)} - {formatDate(comment.suggested_due_date)}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => {
                            setEditingSolutionId(comment.id);
                            setSolutionEstDays(comment.estimated_days || 1);
                            const startDate = comment.suggested_start_date
                              ? new Date(comment.suggested_start_date).toISOString().split("T")[0]
                              : task.start_date
                              ? new Date(task.start_date).toISOString().split("T")[0]
                              : new Date().toISOString().split("T")[0];
                            setSolutionStartDate(startDate);
                            const dueDate = comment.suggested_due_date
                              ? new Date(comment.suggested_due_date).toISOString().split("T")[0]
                              : "";
                            setSolutionDueDate(dueDate);
                          }}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-amber-100 text-amber-700 rounded hover:bg-amber-200"
                        >
                          <Calendar className="w-3 h-3" />
                          Update Task Dates
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Create Task from Suggestion Modal */}
      {showCreateTaskModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold text-gray-900">Create Task from Suggestion</h3>
              <button
                onClick={() => setShowCreateTaskModal(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newTaskFromSuggestion.title}
                  onChange={(e) =>
                    setNewTaskFromSuggestion({ ...newTaskFromSuggestion, title: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Task title"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <MarkdownEditor
                  value={newTaskFromSuggestion.description}
                  onChange={(val) =>
                    setNewTaskFromSuggestion({ ...newTaskFromSuggestion, description: val })
                  }
                  placeholder="Task description..."
                  minHeight={120}
                  maxHeight={200}
                />
              </div>

              {/* Priority and Status */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={newTaskFromSuggestion.priority}
                    onChange={(e) =>
                      setNewTaskFromSuggestion({
                        ...newTaskFromSuggestion,
                        priority: e.target.value as "low" | "medium" | "high" | "urgent",
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={newTaskFromSuggestion.status}
                    onChange={(e) =>
                      setNewTaskFromSuggestion({
                        ...newTaskFromSuggestion,
                        status: e.target.value as "done" | "in_progress" | "on_hold" | "assigned",
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="assigned">Assigned</option>
                    <option value="in_progress">In Progress</option>
                    <option value="on_hold">On Hold</option>
                    <option value="done">Done</option>
                  </select>
                </div>
              </div>

              {/* Project and Due Date */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Project</label>
                  <input
                    type="text"
                    value={newTaskFromSuggestion.project}
                    onChange={(e) =>
                      setNewTaskFromSuggestion({ ...newTaskFromSuggestion, project: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Project name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                  <input
                    type="date"
                    value={newTaskFromSuggestion.due_date}
                    onChange={(e) =>
                      setNewTaskFromSuggestion({ ...newTaskFromSuggestion, due_date: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t bg-gray-50">
              <button
                onClick={() => setShowCreateTaskModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateTaskFromSuggestion}
                disabled={creatingTask || !newTaskFromSuggestion.title.trim()}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creatingTask ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4" />
                )}
                Create Task
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
