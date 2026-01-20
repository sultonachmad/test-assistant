// Task types
export type TaskStatus = "done" | "in_progress" | "on_hold" | "assigned";
export type TaskPriority = "low" | "medium" | "high" | "urgent";
export type RecurrenceType = "none" | "daily" | "weekly" | "biweekly" | "monthly";

export interface Task {
  id: number;
  user_id: number;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  project?: string;  // Project this task belongs to
  start_date?: string;  // When task work started
  due_date?: string;  // Target completion date
  completed_date?: string;  // Actual completion date
  source_type?: string;
  source_id?: string;
  source_url?: string;
  assigned_to?: string;  // Team member this task is assigned to
  tags?: string[];
  // Recurrence fields
  is_recurring?: boolean;
  recurrence_type?: RecurrenceType;
  recurrence_end_date?: string;
  parent_task_id?: number;
  created_at: string;
  updated_at: string;
}

export interface TaskSummary {
  total: number;
  done: number;
  in_progress: number;
  on_hold: number;
  assigned: number;
  overdue: number;
}

export interface TaskList {
  tasks: Task[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// Reminder types
export type ReminderStatus = "pending" | "sent" | "cancelled";
export type ReminderVia = "email" | "calendar" | "inapp";

export interface Reminder {
  id: number;
  user_id: number;
  task_id?: number;
  title: string;
  description?: string;
  remind_at: string;
  remind_via: ReminderVia[];
  is_recurring: boolean;
  recurrence_rule?: string;
  status: ReminderStatus;
  calendar_event_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ReminderList {
  reminders: Reminder[];
  total: number;
  page: number;
  limit: number;
}

// Notification types
export type NotificationType = "reminder" | "task_update" | "sync_complete" | "ai_suggestion" | "system";

export interface Notification {
  id: number;
  user_id: number;
  type: NotificationType;
  title: string;
  message?: string;
  link?: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationList {
  notifications: Notification[];
  unread_count: number;
  total: number;
}

// User types
export interface User {
  id: number;
  email: string;
  name?: string;
  image?: string;
  timezone: string;
  notification_email: boolean;
  notification_calendar: boolean;
  notification_inapp: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserSettings {
  notification_email: boolean;
  notification_calendar: boolean;
  notification_inapp: boolean;
  timezone: string;
}

// Google types
export interface GoogleAuthStatus {
  is_connected: boolean;
  email?: string;
  scopes: string[];
  expires_at?: string;
}

export interface CalendarEvent {
  id: number;
  event_id: string;
  calendar_id: string;
  summary?: string;
  description?: string;
  location?: string;
  start_time?: string;
  end_time?: string;
  attendees: string[];
  is_all_day: boolean;
  status?: string;
}

// Dashboard types
export interface DashboardData {
  task_summary: TaskSummary;
  upcoming_reminders: Reminder[];
  recent_notifications: Notification[];
  calendar_today: CalendarEvent[];
  ai_suggestions: any[];
  sync_status: Record<string, SyncStatus>;
}

export interface SyncStatus {
  status: string;
  items_synced: number;
  last_sync?: string;
  error?: string;
}

// API Response types
export interface ApiResponse<T> {
  status: boolean;
  message?: string;
  data?: T;
}
