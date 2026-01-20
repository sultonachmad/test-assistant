"use client";

import { useEffect, useState } from "react";
import { Plus, Bell, Clock, Check, X } from "lucide-react";
import Header from "@/components/layout/header";
import LoadingSpinner from "@/components/common/loading-spinner";
import { getReminders, createReminder, snoozeReminder, deleteReminder } from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import type { Reminder, ReminderVia } from "@/lib/types";
import toast from "react-hot-toast";

export default function RemindersPage() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewModal, setShowNewModal] = useState(false);
  const [filter, setFilter] = useState<"upcoming" | "all">("upcoming");

  useEffect(() => {
    loadReminders();
  }, [filter]);

  const loadReminders = async () => {
    setLoading(true);
    try {
      const response = await getReminders({
        upcoming_only: filter === "upcoming",
        limit: 50,
      });
      if (response.status && response.data) {
        setReminders(response.data.reminders);
      }
    } catch (error) {
      console.error("Failed to load reminders", error);
      toast.error("Failed to load reminders");
    } finally {
      setLoading(false);
    }
  };

  const handleSnooze = async (id: number) => {
    try {
      await snoozeReminder(id, 15);
      toast.success("Reminder snoozed for 15 minutes");
      loadReminders();
    } catch (error) {
      toast.error("Failed to snooze reminder");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteReminder(id);
      toast.success("Reminder deleted");
      loadReminders();
    } catch (error) {
      toast.error("Failed to delete reminder");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Reminders" />

      <div className="flex-1 p-6 overflow-auto">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilter("upcoming")}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                filter === "upcoming"
                  ? "bg-primary-100 text-primary-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              )}
            >
              Upcoming
            </button>
            <button
              onClick={() => setFilter("all")}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                filter === "all"
                  ? "bg-primary-100 text-primary-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              )}
            >
              All
            </button>
          </div>

          <button
            onClick={() => setShowNewModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Reminder
          </button>
        </div>

        {/* Reminder List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : reminders.length === 0 ? (
          <div className="text-center py-12">
            <Bell className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No reminders</p>
            <button
              onClick={() => setShowNewModal(true)}
              className="mt-4 text-primary-600 hover:text-primary-700 font-medium"
            >
              Create your first reminder
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {reminders.map((reminder) => (
              <div
                key={reminder.id}
                className={cn(
                  "bg-white border rounded-lg p-4",
                  reminder.status === "sent" && "opacity-60"
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">{reminder.title}</h3>
                    {reminder.description && (
                      <p className="text-sm text-gray-500 mt-1">
                        {reminder.description}
                      </p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {formatDate(reminder.remind_at)}
                      </span>
                      <span>
                        via {reminder.remind_via.join(", ")}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {reminder.status === "pending" && (
                      <button
                        onClick={() => handleSnooze(reminder.id)}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                        title="Snooze 15 min"
                      >
                        <Clock className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(reminder.id)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      title="Delete"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Reminder Modal */}
      {showNewModal && (
        <NewReminderModal
          onClose={() => setShowNewModal(false)}
          onCreated={() => {
            setShowNewModal(false);
            loadReminders();
          }}
        />
      )}
    </div>
  );
}

function NewReminderModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [remindAt, setRemindAt] = useState("");
  const [remindVia, setRemindVia] = useState<ReminderVia[]>(["inapp"]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !remindAt) return;

    setLoading(true);
    try {
      await createReminder({
        title: title.trim(),
        description: description.trim() || undefined,
        remind_at: remindAt,
        remind_via: remindVia,
      });
      toast.success("Reminder created");
      onCreated();
    } catch (error) {
      toast.error("Failed to create reminder");
    } finally {
      setLoading(false);
    }
  };

  const toggleVia = (via: ReminderVia) => {
    if (remindVia.includes(via)) {
      setRemindVia(remindVia.filter((v) => v !== via));
    } else {
      setRemindVia([...remindVia, via]);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-md mx-4 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          New Reminder
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              placeholder="Reminder title"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              placeholder="Optional description"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Remind At *
            </label>
            <input
              type="datetime-local"
              value={remindAt}
              onChange={(e) => setRemindAt(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Remind Via
            </label>
            <div className="flex flex-wrap gap-2">
              {(["inapp", "email", "calendar"] as ReminderVia[]).map((via) => (
                <button
                  key={via}
                  type="button"
                  onClick={() => toggleVia(via)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                    remindVia.includes(via)
                      ? "bg-primary-100 text-primary-700"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  )}
                >
                  {via === "inapp" ? "In-App" : via.charAt(0).toUpperCase() + via.slice(1)}
                </button>
              ))}
            </div>
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
              disabled={loading || !title.trim() || !remindAt}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create Reminder"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
