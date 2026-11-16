/**
 * RECLAIM - Popup Controller Script
 * Manages user interactions, timer ticks, primary task setting, and API connectivity indicator.
 */

let timerInterval = null;

async function checkApiHealth() {
  const dot = document.getElementById("api-status-dot");
  const text = document.getElementById("api-status-text");
  try {
    const res = await fetch("http://localhost:8000/api/health");
    if (res.ok) {
      dot.className = "api-dot";
      text.innerText = "FastAPI Backend Online (:8000)";
    } else {
      dot.className = "api-dot offline";
      text.innerText = "API Error";
    }
  } catch (e) {
    dot.className = "api-dot offline";
    text.innerText = "FastAPI Offline (Run uvicorn)";
  }
}

function formatTimer(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

function updateUi(state) {
  if (!state) return;

  const statusBadge = document.getElementById("status-badge");
  const alertCard = document.getElementById("alert-card");
  const alertTitle = document.getElementById("alert-title");
  const alertDesc = document.getElementById("alert-desc");
  const timerDisplay = document.getElementById("interruption-timer");
  const primaryDomain = document.getElementById("primary-domain");
  const primaryCategory = document.getElementById("primary-category");
  const statSwitches = document.getElementById("stat-switches");
  const statEpisodes = document.getElementById("stat-interruptions");
  const btnPauseResume = document.getElementById("btn-pause-resume");
  const btnStop = document.getElementById("btn-stop");

  // Populate Primary Task Info
  primaryDomain.innerText = state.primaryDomain || "Not Selected";
  primaryCategory.innerText = state.primaryCategory || "None";
  statSwitches.innerText = state.totalSwitches || 0;
  statEpisodes.innerText = state.currentEpisodeId ? 1 : 0;

  clearInterval(timerInterval);

  if (state.trackingStatus === "ACTIVE") {
    btnPauseResume.disabled = false;
    btnPauseResume.innerText = "Pause";
    btnStop.disabled = false;

    if (state.isInterrupted) {
      statusBadge.className = "badge badge-interrupted";
      statusBadge.innerText = "INTERRUPTED";

      alertCard.className = "alert-card alert-interrupted-active";
      alertTitle.innerText = "⚠️ Context Switch Detected";
      alertDesc.innerText = `Currently away on ${state.currentDomain || "external tab"}`;
      timerDisplay.style.display = "block";

      const startTime = state.interruptionStartTime || Date.now();
      const updateClock = () => {
        const elapsedSec = (Date.now() - startTime) / 1000;
        timerDisplay.innerText = formatTimer(elapsedSec);
      };
      updateClock();
      timerInterval = setInterval(updateClock, 1000);

    } else {
      statusBadge.className = "badge badge-active";
      statusBadge.innerText = "WORKING";

      alertCard.className = "alert-card alert-working";
      alertTitle.innerText = "Focused on Primary Task";
      alertDesc.innerText = `Active on ${state.primaryDomain}. Automatic tab tracking active.`;
      timerDisplay.style.display = "none";
    }

  } else if (state.trackingStatus === "PAUSED") {
    statusBadge.className = "badge badge-paused";
    statusBadge.innerText = "PAUSED";
    btnPauseResume.disabled = false;
    btnPauseResume.innerText = "Resume";
    btnStop.disabled = false;

    alertCard.className = "alert-card alert-working";
    alertTitle.innerText = "Tracking Suspended";
    alertDesc.innerText = "Monitoring is paused. Context switches will not be logged.";
    timerDisplay.style.display = "none";

  } else {
    // STOPPED
    statusBadge.className = "badge badge-stopped";
    statusBadge.innerText = "STOPPED";
    btnPauseResume.disabled = true;
    btnPauseResume.innerText = "Pause";
    btnStop.disabled = true;

    alertCard.className = "alert-card alert-working";
    alertTitle.innerText = "Tracking Inactive";
    alertDesc.innerText = "Navigate to your work tab and click 'Set Current Tab as Primary Task'.";
    timerDisplay.style.display = "none";
  }
}

async function refreshState() {
  chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
    if (response && response.state) {
      updateUi(response.state);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  checkApiHealth();
  refreshState();

  // Button: Set Primary Tab
  document.getElementById("btn-set-primary").addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "SET_PRIMARY_TAB" }, (response) => {
      if (response && response.success) {
        refreshState();
      }
    });
  });

  // Button: Pause / Resume
  document.getElementById("btn-pause-resume").addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
      const current = response.state.trackingStatus;
      const action = current === "ACTIVE" ? "PAUSE_TRACKING" : "RESUME_TRACKING";
      chrome.runtime.sendMessage({ type: action }, () => refreshState());
    });
  });

  // Button: Stop
  document.getElementById("btn-stop").addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "STOP_TRACKING" }, () => refreshState());
  });

  // Button: Open Dashboard
  document.getElementById("btn-open-dashboard").addEventListener("click", () => {
    chrome.tabs.create({ url: "http://localhost:8501" });
  });
});

