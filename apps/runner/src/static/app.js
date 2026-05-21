(() => {
  const app = document.querySelector(".app");
  if (!app) return;

  const apiJobsUrl = app.dataset.apiJobsUrl || "/api/jobs";
  const state = {
    jobs: [],
    filter: "all",
    query: "",
    selectedJob: null,
    detailRuns: [],
    detailLoading: false,
  };

  const els = {
    listView: document.getElementById("jobs-list-view"),
    detailView: document.getElementById("job-detail-view"),
    body: document.getElementById("jobs-body"),
    summary: document.getElementById("jobs-summary"),
    search: document.getElementById("job-search"),
    syncTime: document.getElementById("sync-time"),
    refresh: document.getElementById("refresh-btn"),
    chips: document.getElementById("filter-chips"),
    detailBack: document.getElementById("detail-back"),
    detailTitle: document.getElementById("detail-title"),
    detailMeta: document.getElementById("detail-meta"),
    detailDesc: document.getElementById("detail-desc"),
    detailRunsBody: document.getElementById("detail-runs-body"),
    footerApi: document.getElementById("footer-api"),
    modal: document.getElementById("run-modal"),
    modalRunId: document.getElementById("modal-run-id"),
    modalNamespace: document.getElementById("modal-namespace"),
    modalGrafana: document.getElementById("modal-grafana"),
    modalClose: document.getElementById("modal-close"),
  };

  function tickClock() {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const ss = String(now.getSeconds()).padStart(2, "0");
    if (els.syncTime) els.syncTime.textContent = `synced ${hh}:${mm}:${ss}`;
  }

  function jobCounts(jobs) {
    return {
      all: jobs.length,
      running: jobs.filter((j) => j.status === "running").length,
      failed: jobs.filter((j) => j.status === "failed").length,
      scheduled: jobs.filter((j) => !j.schedule.manual).length,
      manual: jobs.filter((j) => j.schedule.manual).length,
    };
  }

  function matchesFilter(job) {
    if (state.filter === "running" && job.status !== "running") return false;
    if (state.filter === "failed" && job.status !== "failed") return false;
    if (state.filter === "scheduled" && job.schedule.manual) return false;
    if (state.filter === "manual" && !job.schedule.manual) return false;
    return true;
  }

  function matchesSearch(job) {
    if (!state.query) return true;
    const haystack = [
      job.app,
      job.name,
      job.description,
      job.cronjobName,
      job.lastRun?.id,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(state.query);
  }

  function sparklineHtml(history) {
    const items = history.length ? history : ["pending"];
    return `<div class="sparkline" aria-hidden="true">${items
      .map((item) => {
        const height = item === "success" ? 18 : item === "failed" ? 14 : 10;
        return `<span class="spark-bar ${item}" style="height:${height}px"></span>`;
      })
      .join("")}</div>`;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function formatTimestamp(value) {
    if (!value) return "—";
    try {
      const parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) return escapeHtml(value);
      return escapeHtml(parsed.toLocaleString());
    } catch {
      return escapeHtml(value);
    }
  }

  function runsUrl(app, name) {
    const base = apiJobsUrl.replace(/\/$/, "");
    return `${base}/${encodeURIComponent(app)}/${encodeURIComponent(name)}/runs`;
  }

  function runUrl(app, name) {
    const base = apiJobsUrl.replace(/\/$/, "");
    return `${base}/${encodeURIComponent(app)}/${encodeURIComponent(name)}/run`;
  }

  function showListView() {
    state.selectedJob = null;
    els.listView?.classList.remove("hidden");
    els.detailView?.classList.add("hidden");
    els.detailView?.setAttribute("hidden", "");
    if (els.footerApi) {
      els.footerApi.textContent = `GET /api/jobs · namespace ${app.dataset.namespace || "apps"}`;
    }
  }

  function showDetailView(job) {
    state.selectedJob = job;
    els.listView?.classList.add("hidden");
    els.detailView?.classList.remove("hidden");
    els.detailView?.removeAttribute("hidden");

    if (els.detailTitle) els.detailTitle.textContent = job.name;
    if (els.detailMeta) {
      const schedule = job.schedule.manual ? "manual" : job.schedule.cron;
      els.detailMeta.textContent = `${job.app} · ${schedule} · ${job.schedule.human}`;
    }
    if (els.detailDesc) {
      els.detailDesc.textContent = job.description || "";
      els.detailDesc.hidden = !job.description;
    }
    if (els.footerApi) {
      els.footerApi.textContent = `GET /api/jobs/${job.app}/${job.name}/runs`;
    }
    loadDetailRuns(job);
  }

  function renderDetailRuns() {
    if (!els.detailRunsBody) return;

    if (state.detailLoading) {
      els.detailRunsBody.innerHTML =
        `<tr class="loading-row"><td colspan="5">Loading run history…</td></tr>`;
      return;
    }

    if (!state.detailRuns.length) {
      els.detailRunsBody.innerHTML =
        `<tr class="empty-row"><td colspan="5">No runs recorded for this job yet.</td></tr>`;
      return;
    }

    els.detailRunsBody.innerHTML = state.detailRuns
      .map((run) => {
        const logsLink = run.grafanaUrl
          ? `<a href="${escapeHtml(run.grafanaUrl)}" target="_blank" rel="noopener noreferrer">Grafana</a>`
          : "—";
        return `<tr>
          <td class="mono">${escapeHtml(run.id)}</td>
          <td><span class="status-pill ${escapeHtml(run.status)}">${escapeHtml(run.status)}</span></td>
          <td class="mono">${formatTimestamp(run.startedAt)}</td>
          <td class="mono">${formatTimestamp(run.completedAt)}</td>
          <td>${logsLink}</td>
        </tr>`;
      })
      .join("");
  }

  async function loadDetailRuns(job) {
    state.detailLoading = true;
    renderDetailRuns();
    try {
      const response = await fetch(runsUrl(job.app, job.name));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      state.detailRuns = await response.json();
    } catch (error) {
      els.detailRunsBody.innerHTML =
        `<tr class="empty-row"><td colspan="5">Failed to load runs: ${escapeHtml(error.message)}</td></tr>`;
      state.detailRuns = [];
    } finally {
      state.detailLoading = false;
      if (state.selectedJob === job) renderDetailRuns();
    }
  }

  function render() {
    const visible = state.jobs.filter((job) => matchesFilter(job) && matchesSearch(job));
    const counts = jobCounts(state.jobs);

    document.querySelectorAll("[data-count]").forEach((el) => {
      const key = el.dataset.count;
      if (key) el.textContent = String(counts[key] ?? 0);
    });

    if (els.summary) {
      const scheduled = counts.scheduled;
      const manual = counts.manual;
      els.summary.textContent = `${counts.all} jobs · ${scheduled} scheduled · ${manual} manual · click a job for full history`;
    }

    if (!visible.length) {
      els.body.innerHTML = `<tr class="empty-row"><td colspan="7">No jobs match the current filter.</td></tr>`;
      return;
    }

    els.body.innerHTML = visible
      .map((job) => {
        const isRunning = job.status === "running";
        const scheduleCron = job.schedule.manual ? "manual" : job.schedule.cron;
        const lastRunTime = isRunning
          ? "running now…"
          : job.lastRun?.relative || "—";
        const lastRunId = job.lastRun?.id
          ? job.lastRun.grafanaUrl
            ? `<a href="${escapeHtml(job.lastRun.grafanaUrl)}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">${escapeHtml(job.lastRun.id)}</a>`
            : escapeHtml(job.lastRun.id)
          : "—";

        return `<tr class="job-row" data-app="${escapeHtml(job.app)}" data-name="${escapeHtml(job.name)}">
          <td><span class="app-tag">${escapeHtml(job.app)}</span></td>
          <td>
            <button type="button" class="job-name-link">${escapeHtml(job.name)}</button>
            <span class="job-desc">${escapeHtml(job.description || "")}</span>
          </td>
          <td>
            <span class="schedule-cron">${escapeHtml(scheduleCron)}</span>
            <span class="schedule-human">${escapeHtml(job.schedule.human)}</span>
          </td>
          <td><span class="status-pill ${escapeHtml(job.status)}">${escapeHtml(job.status)}</span></td>
          <td>
            <span class="last-run-time">${escapeHtml(lastRunTime)}</span>
            <span class="last-run-id mono">${lastRunId}</span>
          </td>
          <td>${sparklineHtml(job.history)}</td>
          <td>
            <button
              type="button"
              class="btn-run ${isRunning ? "primary" : ""}"
              data-run-app="${escapeHtml(job.app)}"
              data-run-name="${escapeHtml(job.name)}"
              ${isRunning ? "disabled" : ""}
            >
              ${isRunning ? "Running" : "▶ Run"}
            </button>
          </td>
        </tr>`;
      })
      .join("");

    els.body.querySelectorAll(".job-row").forEach((row) => {
      const appName = row.dataset.app;
      const jobName = row.dataset.name;
      const job = state.jobs.find((item) => item.app === appName && item.name === jobName);
      if (!job) return;

      row.addEventListener("click", () => showDetailView(job));
      row.querySelector(".job-name-link")?.addEventListener("click", (event) => {
        event.stopPropagation();
        showDetailView(job);
      });
    });

    els.body.querySelectorAll("[data-run-app]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.stopPropagation();
        triggerRun(btn.dataset.runApp, btn.dataset.runName);
      });
    });
  }

  async function loadJobs() {
    els.body.innerHTML = `<tr class="loading-row"><td colspan="7">Loading…</td></tr>`;
    try {
      const response = await fetch(apiJobsUrl);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      state.jobs = await response.json();
      if (state.selectedJob) {
        const refreshed = state.jobs.find(
          (job) =>
            job.app === state.selectedJob.app && job.name === state.selectedJob.name,
        );
        if (refreshed) {
          state.selectedJob = refreshed;
          if (els.detailTitle) els.detailTitle.textContent = refreshed.name;
          loadDetailRuns(refreshed);
        }
      }
      if (!state.selectedJob) render();
      tickClock();
    } catch (error) {
      if (!state.selectedJob) {
        els.body.innerHTML = `<tr class="empty-row"><td colspan="7">Failed to load jobs: ${escapeHtml(error.message)}</td></tr>`;
      }
    }
  }

  async function triggerRun(appName, name) {
    const button = els.body.querySelector(
      `[data-run-app="${appName}"][data-run-name="${name}"]`,
    );
    if (button) button.disabled = true;
    try {
      const response = await fetch(runUrl(appName, name), { method: "POST" });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `HTTP ${response.status}`);
      }
      const payload = await response.json();
      showModal(payload);
      await loadJobs();
      if (state.selectedJob?.app === appName && state.selectedJob?.name === name) {
        const refreshed = state.jobs.find((job) => job.app === appName && job.name === name);
        if (refreshed) loadDetailRuns(refreshed);
      }
    } catch (error) {
      alert(`Run failed: ${error.message}`);
      if (button) button.disabled = false;
    }
  }

  function showModal(payload) {
    els.modalRunId.textContent = payload.runId || "—";
    els.modalNamespace.textContent = payload.namespace || "—";
    if (payload.grafanaUrl) {
      els.modalGrafana.href = payload.grafanaUrl;
      els.modalGrafana.classList.remove("hidden");
    } else {
      els.modalGrafana.href = "#";
      els.modalGrafana.classList.add("hidden");
    }
    els.modal.classList.remove("hidden");
  }

  function hideModal() {
    els.modal.classList.add("hidden");
  }

  els.search?.addEventListener("input", (event) => {
    state.query = event.target.value.trim().toLowerCase();
    render();
  });

  els.chips?.addEventListener("click", (event) => {
    const chip = event.target.closest(".chip");
    if (!chip) return;
    state.filter = chip.dataset.filter || "all";
    document.querySelectorAll(".chip").forEach((el) => el.classList.remove("active"));
    chip.classList.add("active");
    render();
  });

  els.refresh?.addEventListener("click", () => {
    loadJobs();
    if (state.selectedJob) loadDetailRuns(state.selectedJob);
  });

  els.detailBack?.addEventListener("click", () => {
    showListView();
    render();
  });

  els.modalClose?.addEventListener("click", hideModal);
  els.modal?.addEventListener("click", (event) => {
    if (event.target === els.modal) hideModal();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!els.modal.classList.contains("hidden")) {
        hideModal();
        return;
      }
      if (state.selectedJob) {
        showListView();
        render();
      }
    }
  });

  loadJobs();
  setInterval(tickClock, 1000);
})();
