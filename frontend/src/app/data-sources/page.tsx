"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileSpreadsheet,
  Plus,
  Trash2,
  RefreshCw,
  ExternalLink,
  Settings,
  ChevronRight,
  Check,
  X,
  Upload,
} from "lucide-react";
import Header from "@/components/layout/header";
import LoadingSpinner from "@/components/common/loading-spinner";
import {
  listSpreadsheets,
  getSpreadsheetInfo,
  getSheetHeaders,
  previewSheetData,
  getTaskFields,
  getSheetSyncConfigs,
  createSheetSyncConfig,
  deleteSheetSyncConfig,
  syncSheetTasks,
} from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import toast from "react-hot-toast";

interface SheetSyncConfig {
  id: number;
  spreadsheet_id: string;
  spreadsheet_name: string;
  spreadsheet_url: string;
  sheet_name: string;
  field_mapping: Record<string, string>;
  auto_sync: boolean;
  sync_interval_minutes: number;
  last_sync: string | null;
  last_sync_count: number;
  is_active: boolean;
}

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

interface TaskField {
  name: string;
  label: string;
  required: boolean;
  description: string;
}

type WizardStep = "select-file" | "select-sheet" | "map-fields" | "confirm";

export default function DataSourcesPage() {
  const [configs, setConfigs] = useState<SheetSyncConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<number | null>(null);

  // Wizard state
  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState<WizardStep>("select-file");
  const [spreadsheets, setSpreadsheets] = useState<Spreadsheet[]>([]);
  const [selectedSpreadsheet, setSelectedSpreadsheet] = useState<Spreadsheet | null>(null);
  const [sheets, setSheets] = useState<SheetInfo[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<SheetInfo | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [previewData, setPreviewData] = useState<{ headers: string[]; rows: string[][]; total_rows: number } | null>(null);
  const [taskFields, setTaskFields] = useState<TaskField[]>([]);
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({});
  const [autoSync, setAutoSync] = useState(true);
  const [wizardLoading, setWizardLoading] = useState(false);

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      const response = await getSheetSyncConfigs();
      if (response.status && response.data) {
        setConfigs(response.data);
      }
    } catch (error) {
      console.error("Failed to load configs", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (configId: number) => {
    setSyncing(configId);
    try {
      await syncSheetTasks(configId);
      toast.success("Sync started in background");
      // Reload configs after a delay
      setTimeout(loadConfigs, 2000);
    } catch (error) {
      toast.error("Failed to start sync");
    } finally {
      setSyncing(null);
    }
  };

  const handleDelete = async (configId: number) => {
    if (!confirm("Are you sure you want to delete this sync configuration?")) return;

    try {
      await deleteSheetSyncConfig(configId);
      toast.success("Configuration deleted");
      loadConfigs();
    } catch (error) {
      toast.error("Failed to delete configuration");
    }
  };

  const openWizard = async () => {
    setShowWizard(true);
    setWizardStep("select-file");
    setSelectedSpreadsheet(null);
    setSelectedSheet(null);
    setHeaders([]);
    setPreviewData(null);
    setFieldMapping({});
    setAutoSync(true);

    // Load spreadsheets and task fields
    setWizardLoading(true);
    try {
      const [spreadsheetsRes, fieldsRes] = await Promise.all([
        listSpreadsheets(),
        getTaskFields(),
      ]);
      if (spreadsheetsRes.status && spreadsheetsRes.data) {
        setSpreadsheets(spreadsheetsRes.data);
      }
      if (fieldsRes.status && fieldsRes.data) {
        setTaskFields(fieldsRes.data);
      }
    } catch (error) {
      toast.error("Failed to load data");
    } finally {
      setWizardLoading(false);
    }
  };

  const selectSpreadsheet = async (spreadsheet: Spreadsheet) => {
    setSelectedSpreadsheet(spreadsheet);
    setWizardLoading(true);
    try {
      const response = await getSpreadsheetInfo(spreadsheet.spreadsheet_id);
      if (response.status && response.data) {
        setSheets(response.data.sheets);
        setWizardStep("select-sheet");
      }
    } catch (error) {
      toast.error("Failed to load spreadsheet info");
    } finally {
      setWizardLoading(false);
    }
  };

  const selectSheet = async (sheet: SheetInfo) => {
    setSelectedSheet(sheet);
    setWizardLoading(true);
    try {
      const [headersRes, previewRes] = await Promise.all([
        getSheetHeaders(selectedSpreadsheet!.spreadsheet_id, sheet.title),
        previewSheetData(selectedSpreadsheet!.spreadsheet_id, sheet.title),
      ]);
      if (headersRes.status && headersRes.data) {
        setHeaders(headersRes.data);
      }
      if (previewRes.status && previewRes.data) {
        setPreviewData(previewRes.data);
      }
      setWizardStep("map-fields");
    } catch (error) {
      toast.error("Failed to load sheet data");
    } finally {
      setWizardLoading(false);
    }
  };

  const handleFieldMappingChange = (taskField: string, sheetColumn: string) => {
    setFieldMapping((prev) => {
      if (!sheetColumn) {
        const { [taskField]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [taskField]: sheetColumn };
    });
  };

  const createConfig = async () => {
    if (!fieldMapping.title) {
      toast.error("Title field mapping is required");
      return;
    }

    setWizardLoading(true);
    try {
      const response = await createSheetSyncConfig({
        spreadsheet_id: selectedSpreadsheet!.spreadsheet_id,
        sheet_name: selectedSheet!.title,
        field_mapping: fieldMapping,
        auto_sync: autoSync,
        sync_interval_minutes: 15,
      });

      if (response.status) {
        toast.success("Sheet sync configuration created");
        setShowWizard(false);
        loadConfigs();
      }
    } catch (error) {
      toast.error("Failed to create configuration");
    } finally {
      setWizardLoading(false);
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
      <Header title="Data Sources" />

      <div className="flex-1 p-6 overflow-auto">
        {/* Bandung Resource Sync Card */}
        <div className="mb-8">
          <Link
            href="/data-sources/bandung-sync"
            className="block bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Upload className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">Bandung Resource Sync</h3>
                  <p className="text-sm text-gray-500">
                    Sync tasks to Google Sheet with assignee-based sheet mapping
                  </p>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400" />
            </div>
          </Link>
        </div>

        {/* Add New Button */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Google Sheets Sync (Import)</h2>
            <p className="text-sm text-gray-500">
              Connect Google Sheets to automatically import tasks
            </p>
          </div>
          <button
            onClick={openWizard}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4" />
            Add Sheet
          </button>
        </div>

        {/* Configs List */}
        {configs.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <FileSpreadsheet className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No sheets connected</h3>
            <p className="text-gray-500 mb-4">
              Connect a Google Sheet to start syncing tasks automatically
            </p>
            <button
              onClick={openWizard}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="w-4 h-4" />
              Add Sheet
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {configs.map((config) => (
              <div
                key={config.id}
                className="bg-white rounded-lg border border-gray-200 p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-green-100 rounded-lg">
                      <FileSpreadsheet className="w-5 h-5 text-green-600" />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {config.spreadsheet_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        Sheet: {config.sheet_name}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                        {config.last_sync ? (
                          <>
                            <span>Last sync: {formatDate(config.last_sync)}</span>
                            <span>{config.last_sync_count} tasks synced</span>
                          </>
                        ) : (
                          <span>Never synced</span>
                        )}
                        {config.auto_sync && (
                          <span className="text-green-600">Auto-sync enabled</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <a
                      href={config.spreadsheet_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                      title="Open in Google Sheets"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    <button
                      onClick={() => handleSync(config.id)}
                      disabled={syncing === config.id}
                      className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
                      title="Sync now"
                    >
                      <RefreshCw
                        className={cn("w-4 h-4", syncing === config.id && "animate-spin")}
                      />
                    </button>
                    <button
                      onClick={() => handleDelete(config.id)}
                      className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Field Mapping Summary */}
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-xs text-gray-500 mb-1">Field Mapping:</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(config.field_mapping).map(([taskField, sheetColumn]) => (
                      <span
                        key={taskField}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-xs"
                      >
                        <span className="font-medium">{taskField}</span>
                        <ChevronRight className="w-3 h-3" />
                        <span>{sheetColumn}</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Wizard Modal */}
      {showWizard && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Add Google Sheet</h2>
                <p className="text-sm text-gray-500">
                  {wizardStep === "select-file" && "Select a spreadsheet to sync"}
                  {wizardStep === "select-sheet" && "Choose which sheet to sync"}
                  {wizardStep === "map-fields" && "Map sheet columns to task fields"}
                  {wizardStep === "confirm" && "Review and confirm"}
                </p>
              </div>
              <button
                onClick={() => setShowWizard(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              {wizardLoading ? (
                <div className="flex items-center justify-center py-12">
                  <LoadingSpinner size="lg" />
                </div>
              ) : (
                <>
                  {/* Step 1: Select File */}
                  {wizardStep === "select-file" && (
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
                              <p className="font-medium text-gray-900 truncate">
                                {spreadsheet.name}
                              </p>
                              <p className="text-sm text-gray-500">
                                Modified: {formatDate(spreadsheet.last_modified)}
                              </p>
                            </div>
                            <ChevronRight className="w-5 h-5 text-gray-400" />
                          </button>
                        ))
                      )}
                    </div>
                  )}

                  {/* Step 2: Select Sheet */}
                  {wizardStep === "select-sheet" && (
                    <div className="space-y-2">
                      <button
                        onClick={() => setWizardStep("select-file")}
                        className="text-sm text-primary-600 hover:text-primary-700 mb-4"
                      >
                        ← Back to spreadsheets
                      </button>
                      <p className="text-sm text-gray-500 mb-2">
                        Selected: <span className="font-medium">{selectedSpreadsheet?.name}</span>
                      </p>
                      {sheets.map((sheet) => (
                        <button
                          key={sheet.sheet_id}
                          onClick={() => selectSheet(sheet)}
                          className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg border border-gray-200"
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
                  )}

                  {/* Step 3: Map Fields */}
                  {wizardStep === "map-fields" && (
                    <div>
                      <button
                        onClick={() => setWizardStep("select-sheet")}
                        className="text-sm text-primary-600 hover:text-primary-700 mb-4"
                      >
                        ← Back to sheets
                      </button>
                      <p className="text-sm text-gray-500 mb-4">
                        Sheet: <span className="font-medium">{selectedSheet?.title}</span>
                        {previewData && (
                          <span className="ml-2">({previewData.total_rows} rows)</span>
                        )}
                      </p>

                      {/* Preview Table */}
                      {previewData && previewData.rows.length > 0 && (
                        <div className="mb-6 overflow-x-auto">
                          <p className="text-sm font-medium text-gray-700 mb-2">Data Preview:</p>
                          <table className="min-w-full text-sm border border-gray-200 rounded">
                            <thead className="bg-gray-50">
                              <tr>
                                {previewData.headers.map((header, i) => (
                                  <th key={i} className="px-3 py-2 text-left font-medium text-gray-700 border-b">
                                    {header}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {previewData.rows.slice(0, 3).map((row, i) => (
                                <tr key={i} className="border-b last:border-b-0">
                                  {row.map((cell, j) => (
                                    <td key={j} className="px-3 py-2 text-gray-600 truncate max-w-[200px]">
                                      {cell || "-"}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Field Mapping */}
                      <div className="space-y-3">
                        <p className="text-sm font-medium text-gray-700">
                          Map sheet columns to task fields:
                        </p>
                        {taskFields.map((field) => (
                          <div key={field.name} className="flex items-center gap-4">
                            <div className="w-32">
                              <span className="text-sm font-medium text-gray-700">
                                {field.label}
                                {field.required && <span className="text-red-500 ml-1">*</span>}
                              </span>
                            </div>
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                            <select
                              value={fieldMapping[field.name] || ""}
                              onChange={(e) => handleFieldMappingChange(field.name, e.target.value)}
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

                      {/* Auto Sync */}
                      <div className="mt-6 flex items-center gap-3">
                        <input
                          type="checkbox"
                          id="autoSync"
                          checked={autoSync}
                          onChange={(e) => setAutoSync(e.target.checked)}
                          className="w-4 h-4 rounded border-gray-300 text-primary-600"
                        />
                        <label htmlFor="autoSync" className="text-sm text-gray-700">
                          Enable auto-sync (every 15 minutes)
                        </label>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            {wizardStep === "map-fields" && !wizardLoading && (
              <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                <button
                  onClick={() => setShowWizard(false)}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={createConfig}
                  disabled={!fieldMapping.title}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  Create Sync
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
