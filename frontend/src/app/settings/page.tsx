"use client";

import { useEffect, useState } from "react";
import { User, Bell, Link2, Check } from "lucide-react";
import Header from "@/components/layout/header";
import LoadingSpinner from "@/components/common/loading-spinner";
import { getUserSettings, updateUserSettings, getGoogleAuthStatus } from "@/lib/api";
import { useGoogleTokenSync } from "@/lib/use-google-token-sync";
import type { UserSettings, GoogleAuthStatus } from "@/lib/types";
import toast from "react-hot-toast";

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [googleStatus, setGoogleStatus] = useState<GoogleAuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Sync Google tokens to backend
  useGoogleTokenSync();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [settingsRes, googleRes] = await Promise.all([
        getUserSettings(),
        getGoogleAuthStatus(),
      ]);
      if (settingsRes.status && settingsRes.data) {
        setSettings(settingsRes.data);
      }
      if (googleRes.status && googleRes.data) {
        setGoogleStatus(googleRes.data);
      }
    } catch (error) {
      console.error("Failed to load settings", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      await updateUserSettings(settings);
      toast.success("Settings saved");
    } catch (error) {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header title="Settings" />

      <div className="flex-1 p-6 overflow-auto">
        <div className="max-w-2xl space-y-6">
          {/* Google Connection */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <Link2 className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-semibold text-gray-900">
                Google Connection
              </h2>
            </div>

            {googleStatus?.is_connected ? (
              <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
                <Check className="w-5 h-5 text-green-600" />
                <div>
                  <p className="font-medium text-green-800">Connected</p>
                  <p className="text-sm text-green-600">{googleStatus.email}</p>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-yellow-50 rounded-lg">
                <p className="text-yellow-800">
                  Google account not connected. Please sign out and sign in again to connect.
                </p>
              </div>
            )}
          </div>

          {/* Notification Settings */}
          {settings && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <Bell className="w-5 h-5 text-gray-500" />
                <h2 className="text-lg font-semibold text-gray-900">
                  Notifications
                </h2>
              </div>

              <div className="space-y-4">
                <label className="flex items-center justify-between">
                  <span className="text-gray-700">Email Notifications</span>
                  <input
                    type="checkbox"
                    checked={settings.notification_email}
                    onChange={(e) =>
                      setSettings({ ...settings, notification_email: e.target.checked })
                    }
                    className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </label>

                <label className="flex items-center justify-between">
                  <span className="text-gray-700">Calendar Event Reminders</span>
                  <input
                    type="checkbox"
                    checked={settings.notification_calendar}
                    onChange={(e) =>
                      setSettings({ ...settings, notification_calendar: e.target.checked })
                    }
                    className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </label>

                <label className="flex items-center justify-between">
                  <span className="text-gray-700">In-App Notifications</span>
                  <input
                    type="checkbox"
                    checked={settings.notification_inapp}
                    onChange={(e) =>
                      setSettings({ ...settings, notification_inapp: e.target.checked })
                    }
                    className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </label>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Timezone
                </label>
                <select
                  value={settings.timezone}
                  onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                >
                  <option value="Asia/Singapore">Asia/Singapore</option>
                  <option value="Asia/Tokyo">Asia/Tokyo</option>
                  <option value="Asia/Jakarta">Asia/Jakarta</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="America/Los_Angeles">America/Los_Angeles</option>
                  <option value="Europe/London">Europe/London</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>

              <button
                onClick={handleSaveSettings}
                disabled={saving}
                className="mt-6 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Settings"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
