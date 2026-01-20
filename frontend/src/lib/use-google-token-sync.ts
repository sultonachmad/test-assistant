"use client";

import { useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import axiosInstance from "./axios-instance";

/**
 * Hook to sync Google OAuth tokens to the backend.
 * Should be used in a layout or top-level component to ensure
 * tokens are synced after login.
 */
export function useGoogleTokenSync() {
  const { data: session, status } = useSession();
  const lastSyncRef = useRef<string | null>(null);

  useEffect(() => {
    async function syncTokens() {
      if (status !== "authenticated" || !session) return;

      // Check if we have all required tokens
      if (!session.accessToken || !session.refreshToken || !session.accessTokenExpires) {
        console.warn("Missing Google tokens in session");
        return;
      }

      // Create a unique key for this token state to avoid duplicate syncs
      const tokenKey = `${session.accessToken}-${session.accessTokenExpires}`;
      if (lastSyncRef.current === tokenKey) {
        return; // Already synced this token
      }

      try {
        // Convert milliseconds to seconds for backend
        const expiresAtSeconds = Math.floor(session.accessTokenExpires / 1000);

        await axiosInstance.post("/api/auth/google/token", {
          access_token: session.accessToken,
          refresh_token: session.refreshToken,
          expires_at: expiresAtSeconds,
          scopes: [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
          ],
        });

        lastSyncRef.current = tokenKey;
        console.log("Google tokens synced to backend");
      } catch (error) {
        console.error("Failed to sync Google tokens:", error);
      }
    }

    syncTokens();
  }, [session, status]);
}
