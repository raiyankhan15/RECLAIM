/**
 * RECLAIM - Background Service Worker (Manifest V3)
 * Automatically monitors tab transitions, detects departure from designated primary task,
 * measures interruption episodes, and streams telemetry to the local FastAPI backend.
 */

const API_BASE_URL = "http://localhost:8000/api";

// Default State
const DEFAULT_STATE = {
  trackingStatus: "STOPPED", // "STOPPED", "ACTIVE", "PAUSED"
  sessionId: null,
  primaryTabId: null,
  primaryUrl: null,
  primaryDomain: null,
  primaryCategory: null,
  currentTabId: null,
  currentDomain: null,
  isInterrupted: false,
  interruptionStartTime: null,
  currentEpisodeId: null,
  episodeSwitches: 0,
  visitedDomains: [],
  totalSwitches: 0,
  lastSwitchTimestamp: Date.now()
};

// Domain Category Mapping (Local privacy classification)
const DOMAIN_CATEGORIES = {
  "Development & Coding": ["github.com", "gitlab.com", "stackoverflow.com", "localhost", "127.0.0.1", "leetcode.com", "kaggle.com", "colab.research.google.com"],
  "Documentation & Research": ["docs.python.org", "developer.mozilla.org", "arxiv.org", "wikipedia.org", "scikit-learn.org", "fastapi.tiangolo.com"],
  "Communication & Messaging": ["web.whatsapp.com", "slack.com", "discord.com", "mail.google.com", "teams.microsoft.com", "web.telegram.org"],
  "Social Media & Entertainment": ["instagram.com", "twitter.com", "x.com", "youtube.com", "reddit.com", "netflix.com", "twitch.tv", "tiktok.com"],
  "General Productivity": ["docs.google.com", "drive.google.com", "notion.so", "figma.com", "trello.com", "linear.app"]
};

function extractDomainAndCategory(rawUrl) {
  if (!rawUrl) return { domain: "blank", category: "Other" };
  try {
    const urlObj = new URL(rawUrl);
    let host = urlObj.hostname.toLowerCase();
    if (host.startsWith("www.")) host = host.substring(4);

    for (const [cat, domains] of Object.entries(DOMAIN_CATEGORIES)) {
      for (const d of domains) {
        if (host === d || host.endsWith("." + d)) {
          return { domain: host, category: cat };
        }
      }
    }
    return { domain: host, category: "Other / General Browsing" };
  } catch (e) {
    return { domain: "internal", category: "Browser Internal" };
  }
}

// Backend API Dispatcher with Safe Fallback
async function postToApi(endpoint, payload) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return await response.json();
  } catch (err) {
    console.warn(`RECLAIM API offline (${endpoint}):`, err.message);
    return null;
  }
}

// 1. Tab Activation Listener (Tab Switch Detection)
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const state = await chrome.storage.local.get(DEFAULT_STATE);
  if (state.trackingStatus !== "ACTIVE") return;

  const now = Date.now();
  const durationOnPreviousTab = Math.max(0, (now - (state.lastSwitchTimestamp || now)) / 1000);

  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (!tab || !tab.url) return;

    const { domain, category } = extractDomainAndCategory(tab.url);
    const isPrimary = (activeInfo.tabId === state.primaryTabId);

    // Filter duplicate activations on the exact same tab within 250ms
    if (activeInfo.tabId === state.currentTabId && durationOnPreviousTab < 0.25) return;

    let isInterrupted = state.isInterrupted;
    let interruptionStartTime = state.interruptionStartTime;
    let currentEpisodeId = state.currentEpisodeId;
    let episodeSwitches = state.episodeSwitches;
    let visitedDomains = [...(state.visitedDomains || [])];
    let totalSwitches = (state.totalSwitches || 0) + 1;

    // CASE 1: Transition FROM Primary TO Interruption Tab
    if (!isPrimary && !isInterrupted) {
      isInterrupted = true;
      interruptionStartTime = now;
      currentEpisodeId = `ep-${state.sessionId}-${now}`;
      episodeSwitches = 1;
      visitedDomains = [domain];

      // Dispatch switch event
      postToApi("/events/tab-switch", {
        session_id: state.sessionId,
        timestamp: new Date(now).toISOString(),
        from_tab_id: state.currentTabId,
        to_tab_id: activeInfo.tabId,
        to_url: tab.url,
        to_domain: domain,
        to_category: category,
        duration_on_tab: durationOnPreviousTab,
        is_primary: false,
        is_interruption: true
      });
    }
    // CASE 2: Multi-tab switching during an ongoing interruption
    else if (!isPrimary && isInterrupted) {
      episodeSwitches += 1;
      if (!visitedDomains.includes(domain)) visitedDomains.push(domain);

      postToApi("/events/tab-switch", {
        session_id: state.sessionId,
        timestamp: new Date(now).toISOString(),
        from_tab_id: state.currentTabId,
        to_tab_id: activeInfo.tabId,
        to_url: tab.url,
        to_domain: domain,
        to_category: category,
        duration_on_tab: durationOnPreviousTab,
        is_primary: false,
        is_interruption: true
      });
    }
    // CASE 3: Returned to Primary Task
    else if (isPrimary && isInterrupted) {
      const episodeDuration = Math.max(0.1, (now - interruptionStartTime) / 1000);

      // Record final return switch
      postToApi("/events/tab-switch", {
        session_id: state.sessionId,
        timestamp: new Date(now).toISOString(),
        from_tab_id: state.currentTabId,
        to_tab_id: activeInfo.tabId,
        to_url: tab.url,
        to_domain: domain,
        to_category: category,
        duration_on_tab: durationOnPreviousTab,
        is_primary: true,
        is_interruption: false
      });

      // Submit completed grouped interruption episode
      postToApi("/events/interruption-episode", {
        session_id: state.sessionId,
        episode_id: currentEpisodeId || `ep-${now}`,
        start_time: new Date(interruptionStartTime).toISOString(),
        end_time: new Date(now).toISOString(),
        duration_sec: Math.round(episodeDuration * 100) / 100,
        switch_count: episodeSwitches,
        visited_domains: visitedDomains,
        primary_interruption_category: category,
        return_latency_sec: 0.0
      });

      // Reset interruption state
      isInterrupted = false;
      interruptionStartTime = null;
      currentEpisodeId = null;
      episodeSwitches = 0;
      visitedDomains = [];
    }

    // Persist updated state
    await chrome.storage.local.set({
      currentTabId: activeInfo.tabId,
      currentDomain: domain,
      isInterrupted,
      interruptionStartTime,
      currentEpisodeId,
      episodeSwitches,
      visitedDomains,
      totalSwitches,
      lastSwitchTimestamp: now
    });

  } catch (err) {
    console.error("Tab activation error:", err);
  }
});

// 2. Window Focus Change Listener
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  const state = await chrome.storage.local.get(DEFAULT_STATE);
  if (state.trackingStatus !== "ACTIVE") return;

  const hasFocus = (windowId !== chrome.windows.WINDOW_ID_NONE);
  postToApi("/events/window-focus", {
    session_id: state.sessionId,
    timestamp: new Date().toISOString(),
    has_focus: hasFocus,
    details: hasFocus ? `Window ${windowId} gained focus` : "Browser window lost focus"
  });
});

// 3. Idle Detection Listener
chrome.idle.onStateChanged.addListener(async (newState) => {
  const state = await chrome.storage.local.get(DEFAULT_STATE);
  if (state.trackingStatus !== "ACTIVE") return;

  postToApi("/events/idle", {
    session_id: state.sessionId,
    timestamp: new Date().toISOString(),
    idle_state: newState,
    details: `User state shifted to ${newState}`
  });
});

// 4. Message Receiver from Popup UI
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  (async () => {
    const state = await chrome.storage.local.get(DEFAULT_STATE);

    if (request.type === "SET_PRIMARY_TAB") {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tabs || tabs.length === 0) {
        sendResponse({ success: false, message: "No active tab found" });
        return;
      }
      const activeTab = tabs[0];
      const { domain, category } = extractDomainAndCategory(activeTab.url);
      const sessionId = state.sessionId || `sess-${Date.now()}`;

      await chrome.storage.local.set({
        primaryTabId: activeTab.id,
        primaryUrl: activeTab.url,
        primaryDomain: domain,
        primaryCategory: category,
        sessionId: sessionId,
        trackingStatus: "ACTIVE",
        totalSwitches: 0,
        isInterrupted: false,
        lastSwitchTimestamp: Date.now()
      });

      // Notify backend
      postToApi("/session/start", {
        session_id: sessionId,
        primary_tab_id: activeTab.id,
        primary_url: activeTab.url,
        primary_domain: domain,
        primary_category: category,
        timestamp: new Date().toISOString()
      });

      sendResponse({ success: true, domain, category, title: activeTab.title });
    }

    else if (request.type === "PAUSE_TRACKING") {
      await chrome.storage.local.set({ trackingStatus: "PAUSED" });
      sendResponse({ success: true, status: "PAUSED" });
    }

    else if (request.type === "RESUME_TRACKING") {
      await chrome.storage.local.set({ trackingStatus: "ACTIVE", lastSwitchTimestamp: Date.now() });
      sendResponse({ success: true, status: "ACTIVE" });
    }

    else if (request.type === "STOP_TRACKING") {
      if (state.sessionId) {
        postToApi("/session/stop", {
          session_id: state.sessionId,
          timestamp: new Date().toISOString()
        });
      }
      await chrome.storage.local.set({
        trackingStatus: "STOPPED",
        isInterrupted: false,
        interruptionStartTime: null,
        currentEpisodeId: null
      });
      sendResponse({ success: true, status: "STOPPED" });
    }

    else if (request.type === "GET_STATUS") {
      sendResponse({ success: true, state });
    }
  })();

  return true; // Keep message channel open for async response
});

