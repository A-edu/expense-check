"use strict";

const STATUS_META = {
  draft: { label: "Draft", tone: "draft" },
  submitted: { label: "Waiting for review", tone: "review" },
  approved: { label: "Approved", tone: "ok" },
  returned: { label: "Returned", tone: "breach" },
};

const CATEGORY_LABELS = {
  meal: "Meal",
  taxi: "Taxi",
  hotel: "Hotel",
  other: "Other",
};

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || "The request failed.");
    this.status = status;
    this.detail = detail || "";
  }
}

/* Small DOM helpers */

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined && text !== null) {
    node.textContent = text;
  }
  return node;
}

function cell(label, text) {
  const node = element("td", `cell-${label}`, text);
  node.dataset.label = label.charAt(0).toUpperCase() + label.slice(1);
  return node;
}

function showMessage(node, message) {
  node.textContent = message;
  node.hidden = message === "";
}

function money(amount) {
  return `${Number(amount).toFixed(2)} SAR`;
}

function plural(count, word) {
  return count === 1 ? word : `${word}s`;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function relativeTime(value) {
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) {
    return "";
  }
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < 60) {
    return `${minutes} min ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours} h ago`;
  }
  const days = Math.round(hours / 24);
  if (days < 7) {
    return `${days} d ago`;
  }
  return formatDate(value);
}

/* Claim sheet */

function statusPill(status) {
  const meta = STATUS_META[status] || { label: status, tone: "draft" };
  return element("span", `pill pill--${meta.tone}`, meta.label);
}

function detailsText(line) {
  const parts = [];
  if (line.people > 1) {
    parts.push(`${line.people} people`);
  }
  if (line.nights > 1) {
    parts.push(`${line.nights} nights`);
  }
  return parts.join(", ");
}

function hasRule(line, ruleId) {
  return (line.flags || []).some((flag) => flag.rule_id === ruleId);
}

function tableHead() {
  const head = document.createElement("thead");
  const row = document.createElement("tr");
  ["Description", "Category", "Details", "Receipt", "Amount"].forEach((label) => {
    row.append(element("th", null, label));
  });
  head.append(row);
  return head;
}

function lineRow(line) {
  const row = element("tr", "line-row");
  const receipt = cell("receipt", line.has_receipt ? "Yes" : "Missing");
  if (!line.has_receipt && hasRule(line, "RCPT-01")) {
    receipt.classList.add("text-breach");
  }
  row.append(
    cell("description", line.description),
    cell("category", CATEGORY_LABELS[line.category] || line.category),
    cell("details", detailsText(line)),
    receipt,
    cell("amount", money(line.amount))
  );
  return row;
}

function flagRow(line) {
  const row = element("tr", "flag-row");
  const holder = document.createElement("td");
  holder.colSpan = 5;
  const flags = line.flags || [];

  if (flags.length === 0) {
    holder.append(element("span", "line-ok", "Within policy"));
  } else {
    const list = element("ul", "flag-list");
    flags.forEach((flag) => {
      const item = element("li", `flag flag--${flag.severity}`);
      item.append(
        element("span", "rule-tag", flag.rule_id),
        element("span", "flag-message", flag.message)
      );
      list.append(item);
    });
    holder.append(list);
  }

  row.append(holder);
  return row;
}

function issueSummary(claim) {
  const violations = Number(claim.violation_count || 0);
  const review = Number(claim.review_count || 0);
  if (violations === 0 && review === 0) {
    return element("span", "text-ok", "No issues found");
  }
  return element(
    "span",
    "issues-text",
    `${violations} ${plural(violations, "violation")}, ${review} for review`
  );
}

function tableFoot(claim) {
  const foot = document.createElement("tfoot");

  const totalRow = element("tr", "total-row");
  const totalLabel = element("th", null, "Total");
  totalLabel.colSpan = 4;
  totalLabel.scope = "row";
  totalRow.append(totalLabel, element("td", "cell-amount", money(claim.total)));

  const issuesRow = element("tr", "issues-row");
  const issues = document.createElement("td");
  issues.colSpan = 5;
  issues.append(issueSummary(claim));
  issuesRow.append(issues);

  foot.append(totalRow, issuesRow);
  return foot;
}

function latestDecision(claim) {
  const decisions = claim.decisions || [];
  return decisions.length > 0 ? decisions[decisions.length - 1] : null;
}

function decisionLine(decision) {
  const approved = decision.decision === "approve";
  const action = approved ? "Approved" : "Returned";
  const comment = decision.comment ? `: ${decision.comment}` : "";
  return element(
    "p",
    `sheet-decision sheet-decision--${approved ? "approved" : "returned"}`,
    `${action} on ${formatDate(decision.decided_at)}${comment}`
  );
}

function claimSummary(claim) {
  const section = element("section", "sheet-summary");
  section.append(
    element("h3", "section-title", "Summary"),
    element("p", "sheet-summary-text", claim.summary),
    element("p", "sheet-note", "Written by the model from the flags above.")
  );
  return section;
}

function renderClaimSheet(claim) {
  const sheet = element("article", "sheet");

  const head = element("header", "sheet-head");
  const identity = element("div", "sheet-identity");
  identity.append(
    element("h2", "sheet-title", `Claim #${claim.id}`),
    element("p", "sheet-meta", `Submitted by ${claim.submitted_by || "unknown"}`),
    element("p", "sheet-meta", `Policy version ${claim.policy_version}`)
  );
  head.append(identity, statusPill(claim.status));
  sheet.append(head);

  const table = element("table", "claim-table");
  const body = document.createElement("tbody");
  (claim.lines || []).forEach((line) => {
    body.append(lineRow(line), flagRow(line));
  });
  table.append(tableHead(), body, tableFoot(claim));
  sheet.append(table, claimSummary(claim));

  const decision = latestDecision(claim);
  if (decision !== null) {
    sheet.append(decisionLine(decision));
  }
  return sheet;
}

/* API */

async function requestJSON(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new ApiError(0, "Could not reach the server. Is it running?");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response));
  }
  return response.json();
}

async function readDetail(response) {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : "";
  } catch (error) {
    return "";
  }
}

function postJSON(url, payload) {
  return requestJSON(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function checkClaim(text, submittedBy) {
  return postJSON("/api/claims/check", { text, submitted_by: submittedBy });
}

function submitClaim(id) {
  return postJSON(`/api/claims/${id}/submit`, {});
}

function fetchClaim(id) {
  return requestJSON(`/api/claims/${id}`);
}

function fetchQueue() {
  return requestJSON("/api/claims?status=submitted");
}

function sendDecision(id, decision, comment) {
  return postJSON(`/api/claims/${id}/decision`, { decision, comment });
}

function errorMessage(error) {
  if (error instanceof ApiError) {
    if (error.status === 502) {
      return "The model did not respond. Try again in a moment.";
    }
    if (error.status === 0) {
      return "Could not reach the server. Is it running?";
    }
    if (error.detail) {
      return error.detail;
    }
  }
  return "Something went wrong. Try again.";
}

/* Staff page */

function initStaffPage() {
  const form = document.getElementById("check-form");
  if (!form) {
    return;
  }

  const nameInput = document.getElementById("your-name");
  const expensesInput = document.getElementById("expenses");
  const checkButton = document.getElementById("check-button");
  const checkStatus = document.getElementById("check-status");
  const checkError = document.getElementById("check-error");
  const claimEmpty = document.getElementById("claim-empty");
  const claimSlot = document.getElementById("claim-slot");
  const claimActions = document.getElementById("claim-actions");
  const claimStatus = document.getElementById("claim-status");
  const claimError = document.getElementById("claim-error");
  const sendButton = document.getElementById("send-button");
  const newButton = document.getElementById("new-button");

  let claim = null;

  function renderClaim() {
    claimSlot.replaceChildren(renderClaimSheet(claim));
    claimSlot.hidden = false;
    claimEmpty.hidden = true;
    claimActions.hidden = false;
  }

  async function check() {
    checkButton.disabled = true;
    checkButton.textContent = "Checking...";
    showMessage(checkError, "");
    showMessage(claimError, "");
    checkStatus.textContent = "Checking your expenses against the policy.";

    try {
      claim = await checkClaim(expensesInput.value, nameInput.value.trim());
      renderClaim();
      sendButton.hidden = false;
      claimStatus.textContent = "";
      checkStatus.textContent = "";
    } catch (error) {
      showMessage(checkError, errorMessage(error));
      checkStatus.textContent = "";
    } finally {
      checkButton.disabled = false;
      checkButton.textContent = "Check claim";
    }
  }

  async function send() {
    if (claim === null) {
      return;
    }
    sendButton.disabled = true;
    showMessage(claimError, "");

    try {
      claim = await submitClaim(claim.id);
      renderClaim();
      sendButton.hidden = true;
      claimStatus.textContent = `Sent to manager. Claim #${claim.id} is waiting for review.`;
    } catch (error) {
      showMessage(claimError, errorMessage(error));
    } finally {
      sendButton.disabled = false;
    }
  }

  function reset() {
    claim = null;
    form.reset();
    claimSlot.replaceChildren();
    claimSlot.hidden = true;
    claimActions.hidden = true;
    claimEmpty.hidden = false;
    checkStatus.textContent = "";
    claimStatus.textContent = "";
    showMessage(checkError, "");
    showMessage(claimError, "");
    nameInput.focus();
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) {
      return;
    }
    check();
  });
  sendButton.addEventListener("click", send);
  newButton.addEventListener("click", reset);
}

/* Review page */

function initReviewPage() {
  const queueList = document.getElementById("queue");
  if (!queueList) {
    return;
  }

  const queueEmpty = document.getElementById("queue-empty");
  const queueError = document.getElementById("queue-error");
  const claimEmpty = document.getElementById("review-empty");
  const claimSlot = document.getElementById("review-slot");
  const decisionPanel = document.getElementById("decision-panel");
  const commentInput = document.getElementById("comment");
  const decisionError = document.getElementById("decision-error");
  const decisionStatus = document.getElementById("decision-status");
  const approveButton = document.getElementById("approve-button");
  const returnButton = document.getElementById("return-button");

  let queue = [];
  let selectedId = null;

  function setBusy(busy) {
    approveButton.disabled = busy;
    returnButton.disabled = busy;
  }

  function queueItem(claim) {
    const item = document.createElement("li");
    const button = element("button", "queue-item");
    button.type = "button";
    if (claim.id === selectedId) {
      button.setAttribute("aria-current", "true");
    }
    button.append(
      element("span", "queue-name", claim.submitted_by || "Unknown"),
      element("span", "queue-total", money(claim.total)),
      queueIssue(claim),
      element("span", "queue-time", relativeTime(claim.created_at))
    );
    button.addEventListener("click", () => {
      decisionStatus.textContent = "";
      selectClaim(claim.id);
    });
    item.append(button);
    return item;
  }

  function queueIssue(claim) {
    const violations = Number(claim.violation_count || 0);
    if (violations === 0) {
      return element("span", "queue-flag queue-flag--ok", "No issues");
    }
    return element(
      "span",
      "queue-flag queue-flag--breach",
      `${violations} ${plural(violations, "violation")}`
    );
  }

  function renderQueue() {
    queueList.replaceChildren();
    queue.forEach((claim) => queueList.append(queueItem(claim)));
    queueEmpty.hidden = queue.length > 0 || !queueError.hidden;
  }

  function showClaim(claim) {
    claimSlot.replaceChildren(renderClaimSheet(claim));
    claimSlot.hidden = false;
    claimEmpty.hidden = true;
    decisionPanel.hidden = false;
    commentInput.value = "";
    showMessage(decisionError, "");
  }

  function clearClaim() {
    selectedId = null;
    claimSlot.replaceChildren();
    claimSlot.hidden = true;
    decisionPanel.hidden = true;
    claimEmpty.hidden = queue.length === 0;
    commentInput.value = "";
    showMessage(decisionError, "");
  }

  async function selectClaim(id) {
    selectedId = id;
    renderQueue();
    try {
      showClaim(await fetchClaim(id));
    } catch (error) {
      clearClaim();
      showMessage(queueError, errorMessage(error));
      renderQueue();
    }
  }

  async function loadQueue(preferredId) {
    try {
      queue = await fetchQueue();
      showMessage(queueError, "");
    } catch (error) {
      queue = [];
      showMessage(queueError, errorMessage(error));
    }

    const preferredIsQueued =
      preferredId !== undefined &&
      preferredId !== null &&
      queue.some((claim) => claim.id === preferredId);
    if (preferredIsQueued) {
      selectedId = preferredId;
    } else if (!queue.some((claim) => claim.id === selectedId)) {
      selectedId = queue.length > 0 ? queue[0].id : null;
    }
    renderQueue();

    if (selectedId === null) {
      clearClaim();
      return;
    }
    await selectClaim(selectedId);
  }

  async function decide(kind) {
    if (selectedId === null) {
      return;
    }
    const comment = commentInput.value.trim();
    showMessage(decisionError, "");
    decisionStatus.textContent = "";

    if (kind === "return" && comment === "") {
      showMessage(decisionError, "Add a comment before returning the claim.");
      commentInput.focus();
      return;
    }

    const position = queue.findIndex((item) => item.id === selectedId);
    const neighbour = queue[position + 1] || queue[position - 1] || null;

    setBusy(true);
    try {
      const claim = await sendDecision(selectedId, kind, comment);
      const message =
        kind === "approve"
          ? "Claim approved."
          : `Claim returned to ${claim.submitted_by || "the submitter"}.`;
      await loadQueue(neighbour === null ? null : neighbour.id);
      decisionStatus.textContent = message;
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        decisionStatus.textContent = "This claim was already decided.";
        await loadQueue(null);
      } else {
        showMessage(decisionError, errorMessage(error));
      }
    } finally {
      setBusy(false);
    }
  }

  approveButton.addEventListener("click", () => decide("approve"));
  returnButton.addEventListener("click", () => decide("return"));
  loadQueue();
}

initStaffPage();
initReviewPage();
