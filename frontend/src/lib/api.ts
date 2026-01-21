import axiosInstance from "./axios-instance";
import type {
  Task, TaskList, TaskSummary, TaskStatus,
  Reminder, ReminderList,
  NotificationList,
  User, UserSettings,
  GoogleAuthStatus,
  DashboardData,
  ApiResponse
} from "./types";

// Dashboard API
export const getDashboard = async (): Promise<ApiResponse<DashboardData>> => {
  const response = await axiosInstance.get("/api/dashboard");
  return response.data;
};

export const getDashboardStats = async (): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.get("/api/dashboard/stats");
  return response.data;
};

// Task API
export const getTasks = async (params?: {
  status?: string;
  priority?: string;
  project?: string;
  assigned_to?: string;
  search?: string;
  page?: number;
  limit?: number;
}): Promise<ApiResponse<TaskList>> => {
  const response = await axiosInstance.get("/api/tasks", { params });
  return response.data;
};

export const getTask = async (id: number): Promise<ApiResponse<Task>> => {
  const response = await axiosInstance.get(`/api/tasks/${id}`);
  return response.data;
};

export const createTask = async (task: Partial<Task>): Promise<ApiResponse<Task>> => {
  const response = await axiosInstance.post("/api/tasks", task);
  return response.data;
};

export const updateTask = async (id: number, task: Partial<Task>): Promise<ApiResponse<Task>> => {
  const response = await axiosInstance.patch(`/api/tasks/${id}`, task);
  return response.data;
};

export const updateTaskStatus = async (id: number, status: TaskStatus): Promise<ApiResponse<Task>> => {
  const response = await axiosInstance.patch(`/api/tasks/${id}/status`, { status });
  return response.data;
};

export const deleteTask = async (id: number): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.delete(`/api/tasks/${id}`);
  return response.data;
};

export const getTaskSummary = async (): Promise<ApiResponse<TaskSummary>> => {
  const response = await axiosInstance.get("/api/tasks/summary");
  return response.data;
};

export const getTaskAssignees = async (): Promise<ApiResponse<string[]>> => {
  const response = await axiosInstance.get("/api/tasks/assignees");
  return response.data;
};

export const getTaskProjects = async (): Promise<ApiResponse<string[]>> => {
  const response = await axiosInstance.get("/api/tasks/projects");
  return response.data;
};

// Reminder API
export const getReminders = async (params?: {
  status?: string;
  upcoming_only?: boolean;
  page?: number;
  limit?: number;
}): Promise<ApiResponse<ReminderList>> => {
  const response = await axiosInstance.get("/api/reminders", { params });
  return response.data;
};

export const getReminder = async (id: number): Promise<ApiResponse<Reminder>> => {
  const response = await axiosInstance.get(`/api/reminders/${id}`);
  return response.data;
};

export const createReminder = async (reminder: Partial<Reminder>): Promise<ApiResponse<Reminder>> => {
  const response = await axiosInstance.post("/api/reminders", reminder);
  return response.data;
};

export const updateReminder = async (id: number, reminder: Partial<Reminder>): Promise<ApiResponse<Reminder>> => {
  const response = await axiosInstance.patch(`/api/reminders/${id}`, reminder);
  return response.data;
};

export const snoozeReminder = async (id: number, minutes: number = 15): Promise<ApiResponse<Reminder>> => {
  const response = await axiosInstance.post(`/api/reminders/${id}/snooze`, { snooze_minutes: minutes });
  return response.data;
};

export const deleteReminder = async (id: number): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.delete(`/api/reminders/${id}`);
  return response.data;
};

// Notification API
export const getNotifications = async (params?: {
  unread_only?: boolean;
  page?: number;
  limit?: number;
}): Promise<ApiResponse<NotificationList>> => {
  const response = await axiosInstance.get("/api/notifications", { params });
  return response.data;
};

export const markNotificationRead = async (id: number): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.patch(`/api/notifications/${id}/read`);
  return response.data;
};

export const markAllNotificationsRead = async (): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.post("/api/notifications/read-all");
  return response.data;
};

export const deleteNotification = async (id: number): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.delete(`/api/notifications/${id}`);
  return response.data;
};

// User API
export const getCurrentUser = async (): Promise<ApiResponse<User>> => {
  const response = await axiosInstance.get("/api/user/me");
  return response.data;
};

export const updateUser = async (user: Partial<User>): Promise<ApiResponse<User>> => {
  const response = await axiosInstance.patch("/api/user/me", user);
  return response.data;
};

export const getUserSettings = async (): Promise<ApiResponse<UserSettings>> => {
  const response = await axiosInstance.get("/api/user/settings");
  return response.data;
};

export const updateUserSettings = async (settings: UserSettings): Promise<ApiResponse<UserSettings>> => {
  const response = await axiosInstance.patch("/api/user/settings", settings);
  return response.data;
};

// Auth API
export const getGoogleAuthStatus = async (): Promise<ApiResponse<GoogleAuthStatus>> => {
  const response = await axiosInstance.get("/api/auth/google/status");
  return response.data;
};

export const saveGoogleToken = async (token: {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  scopes: string[];
}): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.post("/api/auth/google/token", token);
  return response.data;
};

export const revokeGoogleAccess = async (): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.delete("/api/auth/google/revoke");
  return response.data;
};

// Sync API
export const syncAll = async (): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.post("/api/sync/all");
  return response.data;
};

export const syncGmail = async (): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.post("/api/sync/gmail");
  return response.data;
};

export const syncCalendar = async (): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.post("/api/sync/calendar");
  return response.data;
};

export const syncDocuments = async (): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.post("/api/sync/documents");
  return response.data;
};

export const getSyncStatus = async (): Promise<ApiResponse<Record<string, any>>> => {
  const response = await axiosInstance.get("/api/sync/status");
  return response.data;
};

export const getSyncLogs = async (limit: number = 10): Promise<ApiResponse<any[]>> => {
  const response = await axiosInstance.get("/api/sync/logs", { params: { limit } });
  return response.data;
};

// Sheet Sync API
export const getTaskFields = async (): Promise<ApiResponse<any[]>> => {
  const response = await axiosInstance.get("/api/sheets/task-fields");
  return response.data;
};

export const listSpreadsheets = async (limit: number = 20): Promise<ApiResponse<any[]>> => {
  const response = await axiosInstance.get("/api/sheets/spreadsheets", { params: { limit } });
  return response.data;
};

export const getSpreadsheetInfo = async (spreadsheetId: string): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.get(`/api/sheets/spreadsheets/${spreadsheetId}`);
  return response.data;
};

export const getSheetHeaders = async (spreadsheetId: string, sheetName: string): Promise<ApiResponse<string[]>> => {
  const response = await axiosInstance.get(`/api/sheets/spreadsheets/${spreadsheetId}/sheets/${encodeURIComponent(sheetName)}/headers`);
  return response.data;
};

export const previewSheetData = async (spreadsheetId: string, sheetName: string, limit: number = 5): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.get(`/api/sheets/spreadsheets/${spreadsheetId}/sheets/${encodeURIComponent(sheetName)}/preview`, { params: { limit } });
  return response.data;
};

export const getSheetSyncConfigs = async (activeOnly: boolean = true): Promise<ApiResponse<any[]>> => {
  const response = await axiosInstance.get("/api/sheets/configs", { params: { active_only: activeOnly } });
  return response.data;
};

export const getSheetSyncConfig = async (configId: number): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.get(`/api/sheets/configs/${configId}`);
  return response.data;
};

export const createSheetSyncConfig = async (config: {
  spreadsheet_id: string;
  sheet_name: string;
  field_mapping: Record<string, string>;
  auto_sync?: boolean;
  sync_interval_minutes?: number;
}): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.post("/api/sheets/configs", config);
  return response.data;
};

export const updateSheetSyncConfig = async (configId: number, updates: {
  field_mapping?: Record<string, string>;
  auto_sync?: boolean;
  sync_interval_minutes?: number;
}): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.patch(`/api/sheets/configs/${configId}`, updates);
  return response.data;
};

export const deleteSheetSyncConfig = async (configId: number): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.delete(`/api/sheets/configs/${configId}`);
  return response.data;
};

export const syncSheetTasks = async (configId: number): Promise<ApiResponse<any>> => {
  const response = await axiosInstance.post(`/api/sheets/configs/${configId}/sync`);
  return response.data;
};

// AI Assistant API
export interface TaskSuggestion {
  title: string;
  description?: string;
  priority: string;
  due_date_hint?: string;
  source_email_id?: string;
  source_email_subject?: string;
  source_email_sender?: string;
}

export interface EmailSummaryResponse {
  email_count: number;
  date_range: {
    start: string;
    end: string;
  };
  summary: string;
  task_suggestions: TaskSuggestion[];
}

export interface AddTasksResponse {
  added_count: number;
  task_ids: number[];
}

export const getEmailSuggestions = async (params?: {
  start_date?: string;
  end_date?: string;
}): Promise<ApiResponse<EmailSummaryResponse>> => {
  const response = await axiosInstance.get("/api/ai/email-suggestions", { params });
  return response.data;
};

export const addSuggestedTasks = async (data: {
  tasks: TaskSuggestion[];
  project?: string;
}): Promise<ApiResponse<AddTasksResponse>> => {
  const response = await axiosInstance.post("/api/ai/add-suggested-tasks", data);
  return response.data;
};

export const getQuickSummary = async (days: number = 7): Promise<ApiResponse<{
  email_count: number;
  days: number;
  summary: string;
}>> => {
  const response = await axiosInstance.get("/api/ai/quick-summary", { params: { days } });
  return response.data;
};

export const generateTaskDescription = async (data: {
  title: string;
  current_description?: string;
  project?: string;
}): Promise<ApiResponse<{ description: string; suggested_title?: string }>> => {
  const response = await axiosInstance.post("/api/ai/generate-description", data);
  return response.data;
};

// Taiga Integration API
export interface TaigaSyncResult {
  task_id: number;
  task_title: string;
  action: string;
  taiga_id?: number;
  message?: string;
}

export interface TaigaSyncResponse {
  synced_count: number;
  error_count: number;
  results: TaigaSyncResult[];
}

export interface TaigaUpdateResponse {
  updated_count: number;
  results: TaigaSyncResult[];
}

export interface TaigaConfig {
  user_config: {
    taiga_url: string;
    project_id: number;
    is_active: boolean;
    last_sync?: string;
  } | null;
  has_global_config: boolean;
  is_configured: boolean;
}

export const getTaigaConfig = async (): Promise<ApiResponse<TaigaConfig>> => {
  const response = await axiosInstance.get("/api/taiga/config");
  return response.data;
};

export const saveTaigaConfig = async (config: {
  taiga_url: string;
  auth_token: string;
  project_id: number;
}): Promise<ApiResponse<{ project_name: string }>> => {
  const response = await axiosInstance.post("/api/taiga/config", config);
  return response.data;
};

export const syncTasksToTaiga = async (taskIds: number[]): Promise<ApiResponse<TaigaSyncResponse>> => {
  const response = await axiosInstance.post("/api/taiga/sync-tasks", { task_ids: taskIds });
  return response.data;
};

export const updateTasksFromTaiga = async (): Promise<ApiResponse<TaigaUpdateResponse>> => {
  const response = await axiosInstance.post("/api/taiga/update-from-taiga");
  return response.data;
};

export const getLinkedTaigaTasks = async (): Promise<ApiResponse<any[]>> => {
  const response = await axiosInstance.get("/api/taiga/linked-tasks");
  return response.data;
};

// Bandung Resource Sync API
export interface BandungSyncColumnMapping {
  start_date: string;
  hours: string;
  task_details: string;
  status: string;
  links: string;
}

export interface BandungSyncConfig {
  id?: number;
  user_id?: number;
  spreadsheet_id: string;
  spreadsheet_name?: string;
  spreadsheet_url?: string;
  column_mapping: BandungSyncColumnMapping;
  assignee_sheet_mapping: Record<string, string>;
  is_active?: boolean;
  last_sync?: string;
  last_sync_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface BandungSyncResult {
  total_tasks: number;
  synced_tasks: number;
  updated_tasks: number;
  new_tasks: number;
  skipped_tasks: number;
  errors: string[];
  by_sheet: Record<string, number>;
}

export interface BandungSyncTaskPreview {
  task_id: number;
  title: string;
  assigned_to?: string;
  start_date?: string;
  status: string;
  source_url?: string;
  target_sheet?: string;
}

export const getBandungSyncConfig = async (): Promise<ApiResponse<BandungSyncConfig | null>> => {
  const response = await axiosInstance.get("/api/bandung-sync/config");
  return response.data;
};

export const createBandungSyncConfig = async (config: {
  spreadsheet_id: string;
  column_mapping: BandungSyncColumnMapping;
  assignee_sheet_mapping: Record<string, string>;
}): Promise<ApiResponse<BandungSyncConfig>> => {
  const response = await axiosInstance.post("/api/bandung-sync/config", config);
  return response.data;
};

export const updateBandungSyncConfig = async (configId: number, updates: {
  column_mapping?: BandungSyncColumnMapping;
  assignee_sheet_mapping?: Record<string, string>;
  is_active?: boolean;
}): Promise<ApiResponse<BandungSyncConfig>> => {
  const response = await axiosInstance.patch(`/api/bandung-sync/config/${configId}`, updates);
  return response.data;
};

export const deleteBandungSyncConfig = async (configId: number): Promise<ApiResponse<null>> => {
  const response = await axiosInstance.delete(`/api/bandung-sync/config/${configId}`);
  return response.data;
};

export const getBandungSyncAssignees = async (): Promise<ApiResponse<string[]>> => {
  const response = await axiosInstance.get("/api/bandung-sync/assignees");
  return response.data;
};

export const previewBandungSync = async (assignedTo?: string): Promise<ApiResponse<BandungSyncTaskPreview[]>> => {
  const response = await axiosInstance.get("/api/bandung-sync/preview", {
    params: assignedTo ? { assigned_to: assignedTo } : {}
  });
  return response.data;
};

export const syncBandungResource = async (syncAll: boolean = false): Promise<ApiResponse<BandungSyncResult>> => {
  const response = await axiosInstance.post("/api/bandung-sync/sync", null, {
    params: { sync_all: syncAll }
  });
  return response.data;
};

// Task Comments API
import type { TaskComment, TaskCommentListResponse, AICommentResponse, CommentType, TaskSuggestion } from "./types";

export const getTaskComments = async (
  taskId: number,
  commentType?: CommentType
): Promise<ApiResponse<TaskCommentListResponse>> => {
  const response = await axiosInstance.get(`/api/task-comments/${taskId}`, {
    params: commentType ? { comment_type: commentType } : {}
  });
  return response.data;
};

export const createTaskComment = async (data: {
  task_id: number;
  comment_type: CommentType;
  content: string;
  estimated_days?: number;
  suggested_start_date?: string;
  suggested_due_date?: string;
}): Promise<ApiResponse<TaskComment>> => {
  const response = await axiosInstance.post("/api/task-comments/", data);
  return response.data;
};

export const updateTaskComment = async (
  commentId: number,
  data: {
    content?: string;
    estimated_days?: number;
    suggested_start_date?: string;
    suggested_due_date?: string;
  }
): Promise<ApiResponse<TaskComment>> => {
  const response = await axiosInstance.put(`/api/task-comments/${commentId}`, data);
  return response.data;
};

export const deleteTaskComment = async (commentId: number): Promise<ApiResponse<{ deleted: boolean }>> => {
  const response = await axiosInstance.delete(`/api/task-comments/${commentId}`);
  return response.data;
};

export const generateAIComment = async (data: {
  task_id: number;
  comment_type: CommentType;
  prompt?: string;
  selected_comment_ids?: number[];
}): Promise<ApiResponse<AICommentResponse>> => {
  const response = await axiosInstance.post("/api/task-comments/ai-generate", data);
  return response.data;
};

export const generateAndSaveAIComment = async (data: {
  task_id: number;
  comment_type: CommentType;
  prompt?: string;
  selected_comment_ids?: number[];
}): Promise<ApiResponse<TaskComment>> => {
  const response = await axiosInstance.post("/api/task-comments/ai-generate/save", data);
  return response.data;
};

export const suggestTasksFromComments = async (data: {
  task_id: number;
  selected_comment_ids: number[];
  prompt?: string;
}): Promise<ApiResponse<{ suggestions: TaskSuggestion[] }>> => {
  const response = await axiosInstance.post("/api/task-comments/suggest-tasks", data);
  return response.data;
};

export const updateTaskFromSolution = async (data: {
  comment_id: number;
  start_date: string;
  due_date: string;
}): Promise<ApiResponse<{ updated: boolean }>> => {
  const response = await axiosInstance.post("/api/task-comments/update-task-from-solution", data);
  return response.data;
};
