"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import "@uiw/react-md-editor/markdown-editor.css";
import "@uiw/react-markdown-preview/markdown.css";

// Dynamically import to avoid SSR issues
const MDEditor = dynamic(() => import("@uiw/react-md-editor"), { ssr: false });

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: number;
  maxHeight?: number;
  preview?: "edit" | "live" | "preview";
}

export default function MarkdownEditor({
  value,
  onChange,
  placeholder = "Write your content here...",
  minHeight = 150,
  maxHeight = 300,
  preview = "edit",
}: MarkdownEditorProps) {
  const [mode, setMode] = useState<"edit" | "live" | "preview">(preview);

  return (
    <div className="markdown-editor-wrapper" data-color-mode="light">
      <div className="flex items-center justify-end gap-1 mb-1">
        <button
          type="button"
          onClick={() => setMode("edit")}
          className={`px-2 py-0.5 text-xs rounded ${
            mode === "edit"
              ? "bg-primary-100 text-primary-700"
              : "text-gray-500 hover:bg-gray-100"
          }`}
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => setMode("live")}
          className={`px-2 py-0.5 text-xs rounded ${
            mode === "live"
              ? "bg-primary-100 text-primary-700"
              : "text-gray-500 hover:bg-gray-100"
          }`}
        >
          Split
        </button>
        <button
          type="button"
          onClick={() => setMode("preview")}
          className={`px-2 py-0.5 text-xs rounded ${
            mode === "preview"
              ? "bg-primary-100 text-primary-700"
              : "text-gray-500 hover:bg-gray-100"
          }`}
        >
          Preview
        </button>
      </div>
      <MDEditor
        value={value}
        onChange={(val) => onChange(val || "")}
        preview={mode}
        hideToolbar={false}
        textareaProps={{
          placeholder,
        }}
        height={minHeight}
        style={{
          minHeight,
          maxHeight,
        }}
        visibleDragbar={false}
      />
    </div>
  );
}
