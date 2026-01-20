"use client";

import { useEffect, useState } from "react";
import {
  FileSpreadsheet,
  RefreshCw,
  ExternalLink,
  Settings,
  ChevronRight,
  X,
  ArrowLeft,
  Upload,
  AlertCircle,
} from "lucide-react";
import Link from "next/link";
import Header from "@/components/layout/header";
import LoadingSpinner from "@/components/common/loading-spinner";
import {
  listSpreadsheets,
  getSpreadsheetInfo,
  getSheetHeaders,
  getBandungSyncConfig,
  createBandungSyncConfig,
  deleteBandungSyncConfig,
  getBandungSyncAssignees,
  previewBandungSync,
  syncBandungResource,
  BandungSyncConfig,
  BandungSyncColumnMapping,
  BandungSyncTaskPreview,
  BandungSyncResult,
} from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import toast from "react-hot-toast";

interface Spreadsheet {
  spreadsheet_id: string;
  name: string;
  url: string;
  last_modified: string;
}

interface SheetInfo {
  sheet_id: number;
  title: string;
  index: number;
  row_count: number;
  column_count: number;
}

type SetupStep = "select-spreadsheet" | "select-sheet" | "map-assignees" | "map-columns";

export default function BandungSyncPage() {
  const [config, setConfig] = useState<BandungSyncConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<BandungSyncResult | null>(null);

  // Setup wizard state
  const [showSetup, setShowSetup] = useState(false);
  const [setupStep, setSetupStep] = useState<SetupStep>("select-spreadsheet");
  const [spreadsheets, setSpreadsheets] = useState<Spreadsheet[]>([]);
  const [selectedSpreadsheet, setSelectedSpreadsheet] = useState<Spreadsheet | null>(null);
  const [sheets, setSheets] = useState<SheetInfo[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<SheetInfo | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [assignees, setAssignees] = useState<string[]>([]);

  // Column mapping
  const [columnMapping, setColumnMapping] = useState<BandungSyncColumnMapping>({
    start_date: "",
    hours: "",
    task_details: "",
    status: "",
    links: "",
  });

  // Assignee to sheet mapping - now maps to a single selected sheet
  const [assigneeSheetMapping, setAssigneeSheetMapping] = useState<Record<string, string>>({});

  const [setupLoading, setSetupLoading] = useState(false);

  // Preview state
  const [previewTasks, setPreviewTasks] = useState<BandungSyncTaskPreview[]>([]);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await getBandungSyncConfig();
      if (response.status && response.data) {
        setConfig(response.data);
      }
    } catch (error) {
      console.error("Failed to load config", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const response = await syncBandungResource(false);
      if (response.status && response.data) {
        setSyncResult(response.data);
        toast.success(`Synced ${response.data.synced_tasks} tasks to Google Sheet`);
        loadConfig();
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to sync tasks");
    } finally {
      setSyncing(false);
    }
  };

  const handlePreview = async () => {
    try {
      const response = await previewBandungSync();
      if (response.status && response.data) {
        setPreviewTasks(response.data);
        setShowPreview(true);
      }
    } catch (error) {
      toast.error("Failed to load preview");
    }
  };

  const openSetup = async () => {
    setShowSetup(true);
    setSetupStep("select-spreadsheet");
    setSelectedSpreadsheet(null);
    setSelectedSheet(null);
    setHeaders([]);
    setColumnMapping({
      start_date: "",
      hours: "",
      task_details: "",
      status: "",
      links: "",
    });
    setAssigneeSheetMapping({});

    setSetupLoading(true);
    try {
      const [spreadsheetsRes, assigneesRes] = await Promise.all([
        listSpreadsheets(),
        getBandungSyncAssignees(),
      ]);
      if (spreadsheetsRes.status && spreadsheetsRes.data) {
        setSpreadsheets(spreadsheetsRes.data);
      }
      if (assigneesRes.status && assigneesRes.data) {
        setAssignees(assigneesRes.data);
      }
    } catch (error) {
      toast.error("Failed to load data");
    } finally {
      setSetupLoading(false);
    }
  };

  const selectSpreadsheet = async (spreadsheet: Spreadsheet) => {
    setSelectedSpreadsheet(spreadsheet);
    setSetupLoading(true);
    try {
      const response = await getSpreadsheetInfo(spreadsheet.spreadsheet_id);
      if (response.status && response.data) {
        setSheets(response.data.sheets);
        setSetupStep("select-sheet");
      }
    } catch (error) {
      toast.error("Failed to load spreadsheet info");
    } finally {
      setSetupLoading(false);
    }
  };

  const selectSheet = async (sheet: SheetInfo) => {
    setSelectedSheet(sheet);
    setSetupLoading(true);
    try {
      // Load headers from the selected sheet
      const headersRes = await getSheetHeaders(selectedSpreadsheet!.spreadsheet_id, sheet.title);
      if (headersRes.status && headersRes.data) {
        setHeaders(headersRes.data);
      }
      setSetupStep("map-assignees");
    } catch (error) {
      toast.error("Failed to load sheet headers");
    } finally {
      setSetupLoading(false);
    }
  };

  const handleColumnMappingChange = (field: keyof BandungSyncColumnMapping, value: string) => {
    setColumnMapping((prev) => ({ ...prev, [field]: value }));
  };

  const handleAssigneeToggle = (assignee: string, checked: boolean) => {
    setAssigneeSheetMapping((prev) => {
      if (!checked) {
        const { [assignee]: _, ...rest } = prev;
        return rest;
      }
      // Map assignee to the selected sheet
      return { ...prev, [assignee]: selectedSheet!.title };
    });
  };

  const isColumnMappingComplete = () => {
    return (
      columnMapping.start_date &&
      columnMapping.hours &&
      columnMapping.task_details &&
      columnMapping.status &&
      columnMapping.links
    );
  };

  const isAssigneeMappingComplete = () => {
    return Object.keys(assigneeSheetMapping).length > 0;
  };

  const createConfig = async () => {
    if (!isColumnMappingComplete()) {
      toast.error("Please map all required columns");
      return;
    }

    if (!isAssigneeMappingComplete()) {
      toast.error("Please select at least one assignee");
      return;
    }

    setSetupLoading(true);
    try {
      const response = await createBandungSyncConfig({
        spreadsheet_id: selectedSpreadsheet!.spreadsheet_id,
        column_mapping: columnMapping,
        assignee_sheet_mapping: assigneeSheetMapping,
      });

      if (response.status) {
        toast.success("Bandung Resource sync configured successfully");
        setShowSetup(false);
        loadConfig();
      }
    } catch (error) {
      toast.error("Failed to create configuration");
    } finally {
      setSetupLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!config?.id) return;
    if (!confirm("Are you sure you want to delete this sync configuration?")) return;

    try {
      await deleteBandungSyncConfig(config.id);
      toast.success("Configuration deleted");
      setConfig(null);
    } catch (error) {
      toast.error("Failed to delete configuration");
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
      <Header title="Bandung Resource Sync" />

      <div className="flex-1 p-6 overflow-auto">
        {/* Back Link */}
        <Link
          href="/data-sources"
          className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Data Sources
        </Link>

        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Bandung Resource Sync</h2>
            <p className="text-sm text-gray-500">
              Sync tasks to Google Sheet with assignee-based sheet mapping
            </p>
          </div>
          {!config && (
            <button
              onClick={openSetup}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Settings className="w-4 h-4" />
              Configure Sync
            </button>
          )}
        </div>

        {/* Config Display */}
        {config ? (
          <div className="space-y-6">
            {/* Config Card */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <FileSpreadsheet className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{config.spreadsheet_name}</h3>
                    <a
                      href={config.spreadsheet_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary-600 hover:text-primary-700 inline-flex items-center gap-1"
                    >
                      Open in Google Sheets
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePreview}
                    className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
                  >
                    Preview
                  </button>
                  <button
                    onClick={handleSync}
                    disabled={syncing}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    <RefreshCw className={cn("w-4 h-4", syncing && "animate-spin")} />
                    {syncing ? "Syncing..." : "Sync Now"}
                  </button>
                  <button
                    onClick={handleDelete}
                    className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {/* Sync Status */}
              <div className="flex items-center gap-6 text-sm text-gray-500 mb-4">
                {config.last_sync ? (
                  <>
                    <span>Last sync: {formatDate(config.last_sync)}</span>
                    <span>{config.last_sync_count} tasks synced</span>
                  </>
                ) : (
                  <span>Never synced</span>
                )}
              </div>

              {/* Assignee Mapping */}
              <div className="border-t border-gray-100 pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Assignee → Sheet Mapping</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(config.assignee_sheet_mapping).map(([assignee, sheet]) => (
                    <span
                      key={assignee}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs"
                    >
                      <span className="font-medium">{assignee}</span>
                      <ChevronRight className="w-3 h-3" />
                      <span>{sheet}</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Column Mapping */}
              <div className="border-t border-gray-100 pt-4 mt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Column Mapping</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(config.column_mapping).map(([field, column]) => (
                    <span
                      key={field}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-xs"
                    >
                      <span className="font-medium capitalize">{field.replace("_", " ")}</span>
                      <ChevronRight className="w-3 h-3" />
                      <span>{column}</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Sync Result */}
            {syncResult && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Sync Result</h4>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-semibold text-gray-900">{syncResult.total_tasks}</div>
                    <div className="text-xs text-gray-500">Total Tasks</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-semibold text-green-600">{syncResult.synced_tasks}</div>
                    <div className="text-xs text-gray-500">Synced</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-semibold text-blue-600">{syncResult.new_tasks}</div>
                    <div className="text-xs text-gray-500">New</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-semibold text-yellow-600">{syncResult.updated_tasks}</div>
                    <div className="text-xs text-gray-500">Updated</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-semibold text-gray-400">{syncResult.skipped_tasks}</div>
                    <div className="text-xs text-gray-500">Skipped</div>
                  </div>
                </div>

                {Object.keys(syncResult.by_sheet).length > 0 && (
                  <div className="border-t border-gray-100 pt-3">
                    <p className="text-xs text-gray-500 mb-2">By Sheet:</p>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(syncResult.by_sheet).map(([sheet, count]) => (
                        <span key={sheet} className="px-2 py-1 bg-gray-100 rounded text-xs">
                          {sheet}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {syncResult.errors.length > 0 && (
                  <div className="border-t border-gray-100 pt-3 mt-3">
                    <p className="text-xs text-red-600 mb-2">Errors:</p>
                    <ul className="text-xs text-red-500 space-y-1">
                      {syncResult.errors.map((error, i) => (
                        <li key={i} className="flex items-start gap-1">
                          <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          {error}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Not configured</h3>
            <p className="text-gray-500 mb-4">
              Configure Bandung Resource sync to start syncing tasks to Google Sheets
            </p>
            <button
              onClick={openSetup}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Settings className="w-4 h-4" />
              Configure Sync
            </button>
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Task Preview</h2>
              <button onClick={() => setShowPreview(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 max-h-[70vh] overflow-y-auto">
              {previewTasks.length === 0 ? (
                <p className="text-center text-gray-500">No tasks with start date found</p>
              ) : (
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-gray-700">Title</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-700">Assigned To</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-700">Start Date</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-700">Status</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-700">Target Sheet</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {previewTasks.map((task) => (
                      <tr key={task.task_id}>
                        <td className="px-3 py-2 text-gray-900">{task.title}</td>
                        <td className="px-3 py-2 text-gray-600">{task.assigned_to || "-"}</td>
                        <td className="px-3 py-2 text-gray-600">{task.start_date || "-"}</td>
                        <td className="px-3 py-2 text-gray-600">{task.status}</td>
                        <td className="px-3 py-2">
                          {task.target_sheet ? (
                            <span className="text-green-600">{task.target_sheet}</span>
                          ) : (
                            <span className="text-gray-400">Not mapped</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
              <button
                onClick={() => setShowPreview(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Setup Wizard */}
      {showSetup && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Configure Bandung Resource Sync</h2>
                <p className="text-sm text-gray-500">
                  {setupStep === "select-spreadsheet" && "Step 1: Select Google Sheet"}
                  {setupStep === "select-sheet" && "Step 2: Select sheet tab"}
                  {setupStep === "map-assignees" && "Step 3: Select assignees to sync"}
                  {setupStep === "map-columns" && "Step 4: Map columns for task data"}
                </p>
              </div>
              <button onClick={() => setShowSetup(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 max-h-[60vh] overflow-y-auto">
              {setupLoading ? (
                <div className="flex items-center justify-center py-12">
                  <LoadingSpinner size="lg" />
                </div>
              ) : (
                <>
                  {/* Step 1: Select Spreadsheet */}
                  {setupStep === "select-spreadsheet" && (
                    <div className="space-y-2">
                      {spreadsheets.length === 0 ? (
                        <p className="text-gray-500 text-center py-8">
                          No spreadsheets found. Make sure you have access to Google Sheets.
                        </p>
                      ) : (
                        spreadsheets.map((spreadsheet) => (
                          <button
                            key={spreadsheet.spreadsheet_id}
                            onClick={() => selectSpreadsheet(spreadsheet)}
                            className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg border border-gray-200 text-left"
                          >
                            <FileSpreadsheet className="w-8 h-8 text-green-600" />
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-900 truncate">{spreadsheet.name}</p>
                              <p className="text-sm text-gray-500">Modified: {formatDate(spreadsheet.last_modified)}</p>
                            </div>
                            <ChevronRight className="w-5 h-5 text-gray-400" />
                          </button>
                        ))
                      )}
                    </div>
                  )}

                  {/* Step 2: Select Sheet Tab */}
                  {setupStep === "select-sheet" && (
                    <div>
                      <button
                        onClick={() => setSetupStep("select-spreadsheet")}
                        className="text-sm text-primary-600 hover:text-primary-700 mb-4"
                      >
                        ← Back to spreadsheets
                      </button>
                      <p className="text-sm text-gray-500 mb-4">
                        Selected: <span className="font-medium">{selectedSpreadsheet?.name}</span>
                      </p>

                      <p className="text-sm font-medium text-gray-700 mb-3">
                        Select the sheet tab to sync tasks to:
                      </p>

                      <div className="space-y-2">
                        {sheets.map((sheet) => (
                          <button
                            key={sheet.sheet_id}
                            onClick={() => selectSheet(sheet)}
                            className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg border border-gray-200 text-left"
                          >
                            <div>
                              <p className="font-medium text-gray-900">{sheet.title}</p>
                              <p className="text-sm text-gray-500">
                                {sheet.row_count} rows × {sheet.column_count} columns
                              </p>
                            </div>
                            <ChevronRight className="w-5 h-5 text-gray-400" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Step 3: Map Assignees */}
                  {setupStep === "map-assignees" && (
                    <div>
                      <button
                        onClick={() => setSetupStep("select-sheet")}
                        className="text-sm text-primary-600 hover:text-primary-700 mb-4"
                      >
                        ← Back to sheet selection
                      </button>
                      <p className="text-sm text-gray-500 mb-4">
                        Sheet: <span className="font-medium">{selectedSheet?.title}</span>
                      </p>

                      <div className="space-y-4">
                        <p className="text-sm font-medium text-gray-700">
                          Select which assignees should sync to this sheet:
                        </p>

                        {assignees.length === 0 ? (
                          <p className="text-gray-500 text-center py-4">
                            No assignees found in your tasks. Add tasks with assigned_to field first.
                          </p>
                        ) : (
                          <div className="space-y-2">
                            {assignees.map((assignee) => (
                              <label
                                key={assignee}
                                className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer"
                              >
                                <input
                                  type="checkbox"
                                  checked={assignee in assigneeSheetMapping}
                                  onChange={(e) => handleAssigneeToggle(assignee, e.target.checked)}
                                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                                />
                                <span className="font-medium text-gray-900">{assignee}</span>
                              </label>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Step 4: Map Columns */}
                  {setupStep === "map-columns" && (
                    <div>
                      <button
                        onClick={() => setSetupStep("map-assignees")}
                        className="text-sm text-primary-600 hover:text-primary-700 mb-4"
                      >
                        ← Back to assignee selection
                      </button>
                      <p className="text-sm text-gray-500 mb-4">
                        Sheet: <span className="font-medium">{selectedSheet?.title}</span>
                      </p>

                      <div className="space-y-4">
                        <p className="text-sm font-medium text-gray-700">
                          Map your sheet columns to task fields:
                        </p>

                        {[
                          { field: "start_date", label: "Start Date" },
                          { field: "hours", label: "Hours (will be set to 8)" },
                          { field: "task_details", label: "Task Details (Title)" },
                          { field: "status", label: "Status" },
                          { field: "links", label: "Links (Taiga URL)" },
                        ].map(({ field, label }) => (
                          <div key={field} className="flex items-center gap-4">
                            <div className="w-48">
                              <span className="text-sm font-medium text-gray-700">{label}</span>
                            </div>
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                            <select
                              value={columnMapping[field as keyof BandungSyncColumnMapping] || ""}
                              onChange={(e) =>
                                handleColumnMappingChange(field as keyof BandungSyncColumnMapping, e.target.value)
                              }
                              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                            >
                              <option value="">-- Select column --</option>
                              {headers.map((header) => (
                                <option key={header} value={header}>
                                  {header}
                                </option>
                              ))}
                            </select>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            {!setupLoading && (
              <div className="flex justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
                <button
                  onClick={() => setShowSetup(false)}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>

                {setupStep === "map-assignees" && (
                  <button
                    onClick={() => setSetupStep("map-columns")}
                    disabled={!isAssigneeMappingComplete()}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    Next: Map Columns
                  </button>
                )}

                {setupStep === "map-columns" && (
                  <button
                    onClick={createConfig}
                    disabled={!isColumnMappingComplete()}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    Create Configuration
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
