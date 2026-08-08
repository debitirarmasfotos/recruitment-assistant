/*
 * Recruitment Assistant - frontend logic (vanilla JS, no framework, no build step).
 *
 * Contract (from project-context/2.build/backend.md and sad.md section 4):
 *   POST /api/recommend  (same origin, no CORS)
 *   Request:  { job_requirements: string, criteria?: string[], top_n?: number }
 *   Success:  { shortlist: [ { candidate, rank, score, rationale,
 *                              criteria_breakdown: [ { criterion, result, evidence } ] } ],
 *               run_id: string, status: "ok", notes?: string }
 *   Empty:    status "ok" with empty shortlist and an explanatory notes field.
 *   Error:    { error: { code: string, message: string } } with an HTTP error status.
 *
 * The frontend never wires backend logic; it only sends the payload and renders
 * the JSON response. It handles loading, success, empty, and error states honestly.
 */

(function () {
  "use strict";

  var RECOMMEND_ENDPOINT = "/api/recommend";

  var form = document.getElementById("recommend-form");
  var submitBtn = document.getElementById("submit-btn");
  var statusLine = document.getElementById("status-line");
  var resultsEl = document.getElementById("results");

  // Map the backend result token to a human label and a CSS modifier class.
  var RESULT_LABELS = {
    met: "Met",
    partially_met: "Partially met",
    missed: "Missed",
  };

  /** Split the criteria textarea into a clean list (by newline or comma). */
  function parseCriteria(raw) {
    if (!raw) {
      return [];
    }
    return raw
      .split(/[\n,]+/)
      .map(function (item) {
        return item.trim();
      })
      .filter(function (item) {
        return item.length > 0;
      });
  }

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    if (isLoading) {
      statusLine.textContent = "Running the crew. This can take a moment...";
      statusLine.className = "status-line status-loading";
    } else {
      statusLine.textContent = "";
      statusLine.className = "status-line";
    }
  }

  function clearResults() {
    resultsEl.innerHTML = "";
  }

  /** Render a plain message block (used for errors and empty results). */
  function renderMessage(kind, title, message) {
    clearResults();
    var box = document.createElement("div");
    box.className = "card message message-" + kind;

    var heading = document.createElement("h2");
    heading.textContent = title;
    box.appendChild(heading);

    if (message) {
      var p = document.createElement("p");
      p.textContent = message;
      box.appendChild(p);
    }
    resultsEl.appendChild(box);
  }

  /** Build the per-criterion breakdown list for one candidate. */
  function renderBreakdown(breakdown) {
    var wrap = document.createElement("div");
    wrap.className = "breakdown";

    if (!Array.isArray(breakdown) || breakdown.length === 0) {
      var none = document.createElement("p");
      none.className = "hint";
      none.textContent = "No per-criterion breakdown was provided.";
      wrap.appendChild(none);
      return wrap;
    }

    var title = document.createElement("h4");
    title.className = "breakdown-title";
    title.textContent = "Criteria breakdown";
    wrap.appendChild(title);

    var list = document.createElement("ul");
    list.className = "criteria-list";

    breakdown.forEach(function (item) {
      var li = document.createElement("li");
      li.className = "criterion";

      var resultKey = String(item && item.result ? item.result : "").toLowerCase();
      var label = RESULT_LABELS[resultKey] || (item && item.result) || "Unknown";

      var badge = document.createElement("span");
      badge.className = "badge badge-" + (RESULT_LABELS[resultKey] ? resultKey : "unknown");
      badge.textContent = label;
      li.appendChild(badge);

      var name = document.createElement("span");
      name.className = "criterion-name";
      name.textContent = (item && item.criterion) || "(unnamed criterion)";
      li.appendChild(name);

      if (item && item.evidence) {
        var ev = document.createElement("p");
        ev.className = "criterion-evidence";
        ev.textContent = item.evidence;
        li.appendChild(ev);
      }
      list.appendChild(li);
    });

    wrap.appendChild(list);
    return wrap;
  }

  /** Derive a readable display name/title from the candidate object. */
  function candidateHeading(candidate, rank) {
    var name = "";
    var title = "";
    if (candidate && typeof candidate === "object") {
      name = candidate.name || candidate.id || "";
      title = candidate.title || candidate.role || "";
    } else if (typeof candidate === "string") {
      name = candidate;
    }
    if (!name) {
      name = "Candidate " + rank;
    }
    return { name: name, title: title };
  }

  /** Render one candidate card. */
  function renderCandidate(entry, index) {
    var article = document.createElement("article");
    article.className = "candidate";

    var rank = entry && entry.rank != null ? entry.rank : index + 1;
    var heading = candidateHeading(entry ? entry.candidate : null, rank);

    var head = document.createElement("div");
    head.className = "candidate-head";

    var rankBadge = document.createElement("span");
    rankBadge.className = "rank";
    rankBadge.textContent = "#" + rank;
    head.appendChild(rankBadge);

    var nameWrap = document.createElement("div");
    nameWrap.className = "candidate-id";

    var nameEl = document.createElement("h3");
    nameEl.className = "candidate-name";
    nameEl.textContent = heading.name;
    nameWrap.appendChild(nameEl);

    if (heading.title) {
      var titleEl = document.createElement("p");
      titleEl.className = "candidate-title";
      titleEl.textContent = heading.title;
      nameWrap.appendChild(titleEl);
    }
    head.appendChild(nameWrap);

    if (entry && entry.score != null) {
      var score = document.createElement("span");
      score.className = "score";
      score.textContent = "Score " + entry.score;
      head.appendChild(score);
    }

    article.appendChild(head);

    if (entry && entry.rationale) {
      var rationale = document.createElement("p");
      rationale.className = "rationale";
      rationale.textContent = entry.rationale;
      article.appendChild(rationale);
    }

    article.appendChild(renderBreakdown(entry ? entry.criteria_breakdown : null));
    return article;
  }

  /** Render the full ranked shortlist on a successful, non-empty response. */
  function renderShortlist(data) {
    clearResults();

    var header = document.createElement("div");
    header.className = "results-header";

    var h2 = document.createElement("h2");
    h2.textContent = "Ranked shortlist (" + data.shortlist.length + ")";
    header.appendChild(h2);

    if (data.run_id) {
      var runId = document.createElement("span");
      runId.className = "run-id";
      runId.textContent = "run_id: " + data.run_id;
      header.appendChild(runId);
    }
    resultsEl.appendChild(header);

    if (data.notes) {
      var notes = document.createElement("p");
      notes.className = "notes";
      notes.textContent = data.notes;
      resultsEl.appendChild(notes);
    }

    var reminder = document.createElement("p");
    reminder.className = "hitl-note hitl-note-results";
    reminder.textContent =
      "Reminder: these are recommendations only. A human reviewer makes the final hiring decision.";
    resultsEl.appendChild(reminder);

    var list = document.createElement("div");
    list.className = "candidate-list";
    data.shortlist.forEach(function (entry, index) {
      list.appendChild(renderCandidate(entry, index));
    });
    resultsEl.appendChild(list);
  }

  function handleSuccess(data) {
    var shortlist = data && Array.isArray(data.shortlist) ? data.shortlist : [];
    if (shortlist.length === 0) {
      renderMessage(
        "empty",
        "No strong matches",
        (data && data.notes) ||
          "The crew ran successfully but found no candidates that strongly match these requirements. Try broadening the requirements or criteria."
      );
      return;
    }
    renderShortlist(data);
  }

  /** Turn a FastAPI 422 validation body ({ detail: ... }) into a readable string. */
  function formatValidationDetail(detail) {
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map(function (item) {
          var field =
            item && Array.isArray(item.loc)
              ? item.loc[item.loc.length - 1]
              : "";
          var msg = (item && item.msg) || "invalid value";
          return field ? field + ": " + msg : msg;
        })
        .join("; ");
    }
    return "";
  }

  function handleError(payload, httpStatus) {
    var message = "The request failed. Please try again.";
    var code = "";
    if (payload && payload.error && payload.error.message) {
      // Custom backend envelope: { error: { code, message } }.
      message = payload.error.message;
      code = payload.error.code || "";
    } else if (payload && payload.detail) {
      // FastAPI validation envelope: { detail: [...] } (HTTP 422).
      var detailMsg = formatValidationDetail(payload.detail);
      if (detailMsg) {
        message = detailMsg;
        code = httpStatus === 422 ? "invalid_input" : code;
      }
    } else if (httpStatus) {
      message = "The server returned an error (HTTP " + httpStatus + ").";
    }
    var title = code ? "Error: " + code : "Something went wrong";
    renderMessage("error", title, message);
  }

  function onSubmit(event) {
    event.preventDefault();

    var jobRequirements = document.getElementById("job_requirements").value.trim();
    var criteriaRaw = document.getElementById("criteria").value;
    var topNRaw = document.getElementById("top_n").value;

    if (!jobRequirements) {
      renderMessage(
        "error",
        "Job requirements are required",
        "Please describe the role, key skills, and must-haves before searching."
      );
      return;
    }

    var payload = { job_requirements: jobRequirements };

    var criteria = parseCriteria(criteriaRaw);
    if (criteria.length > 0) {
      payload.criteria = criteria;
    }

    var topN = parseInt(topNRaw, 10);
    if (!isNaN(topN)) {
      payload.top_n = topN;
    }

    setLoading(true);
    clearResults();

    fetch(RECOMMEND_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return null;
          })
          .then(function (body) {
            return { ok: response.ok, status: response.status, body: body };
          });
      })
      .then(function (result) {
        if (result.ok && result.body && !result.body.error) {
          handleSuccess(result.body);
        } else {
          handleError(result.body, result.status);
        }
      })
      .catch(function () {
        renderMessage(
          "error",
          "Network error",
          "Could not reach the server. Check that the service is running and try again."
        );
      })
      .then(function () {
        setLoading(false);
      });
  }

  form.addEventListener("submit", onSubmit);
})();
