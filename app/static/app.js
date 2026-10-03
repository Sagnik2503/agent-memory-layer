(function () {
  "use strict";

  var MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

  function monthParam() {
    return new URLSearchParams(window.location.search).get("month");
  }

  function selectedMonth() {
    var raw = monthParam();
    if (raw && MONTH_PATTERN.test(raw)) return raw;
    return null;
  }

  function currentMonth() {
    var now = new Date();
    return now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0");
  }

  function activeMonth() {
    return selectedMonth() || currentMonth();
  }

  function shiftMonth(month, delta) {
    var parts = month.split("-");
    var shifted = new Date(Number(parts[0]), Number(parts[1]) - 1 + delta, 1);
    return (
      shifted.getFullYear() +
      "-" +
      String(shifted.getMonth() + 1).padStart(2, "0")
    );
  }

  function syncNavLinks() {
    var month = activeMonth();
    document.querySelectorAll(".site-nav a, .wordmark").forEach(function (link) {
      var url = new URL(link.getAttribute("href"), window.location.origin);
      url.searchParams.set("month", month);
      link.setAttribute("href", url.pathname + "?" + url.searchParams.toString());
    });
  }

  function monthLabel(month) {
    var parts = month.split("-");
    var date = new Date(Number(parts[0]), Number(parts[1]) - 1, 1);
    return date.toLocaleDateString("en-GB", { month: "long", year: "numeric" });
  }

  function renderMonthLabels() {
    var label = monthLabel(activeMonth());
    document.querySelectorAll(".month-label").forEach(function (node) {
      node.textContent = label;
    });
  }

  function formatMoney(amount, currency) {
    var code = currency || "INR";
    try {
      return new Intl.NumberFormat("en", {
        style: "currency",
        currency: code,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch (e) {
      return amount + " " + code;
    }
  }

  function formatDay(isoDate) {
    if (!isoDate) return "—";
    var parts = isoDate.split("-");
    var date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function currencyPill(currency) {
    var code = currency || "INR";
    return el("span", "pill pill-" + code.toLowerCase(), code);
  }

  function renderEmptyState(container, message) {
    container.replaceChildren(el("p", "muted empty-state", message));
  }

  function renderTotals(container, totals, label) {
    var currencies = Object.keys(totals);
    if (!currencies.length) {
      renderEmptyState(container, "No spending recorded for " + label + ".");
      return;
    }

    container.replaceChildren();
    currencies.forEach(function (currency) {
      var item = el("span", "total");
      item.append(
        currencyPill(currency),
        document.createTextNode(formatMoney(totals[currency], currency))
      );
      container.append(item);
    });
  }

  var BUDGET_WARNING_PERCENT = 80;

  function categoryLabel(category) {
    return category ? category.replace(/_/g, " ") : "Overall";
  }

  function renderBudgetStatus(container, statuses) {
    if (!statuses.length) {
      renderEmptyState(container, "No budgets set.");
      return;
    }

    container.replaceChildren();
    statuses.forEach(function (status) {
      var percent = Math.max(0, status.percentage_used);
      var isOver = !!status.is_over_budget;
      var isWarn = !isOver && percent >= BUDGET_WARNING_PERCENT;
      var currency = status.currency;
      var label = categoryLabel(status.category);

      var item = el(
        "div",
        "budget" + (isOver ? " budget-over" : isWarn ? " budget-warn" : "")
      );

      var head = el("div", "budget-head");
      head.append(
        el("span", "budget-label", label),
        el(
          "span",
          "budget-figures mono",
          formatMoney(status.spent_amount, currency) +
            " of " +
            formatMoney(status.budget_amount, currency)
        )
      );

      var track = el("div", "budget-track");
      track.setAttribute("role", "progressbar");
      track.setAttribute("aria-label", label + " budget");
      track.setAttribute("aria-valuemin", "0");
      track.setAttribute("aria-valuemax", "100");
      track.setAttribute("aria-valuenow", String(Math.min(Math.round(percent), 100)));
      var fill = el("div", "budget-fill");
      fill.style.width = Math.min(percent, 100) + "%";
      track.append(fill);

      var foot = el("div", "budget-foot");
      foot.append(el("span", "budget-pct mono", Math.round(percent) + "% used"));
      if (isOver) {
        foot.append(
          el(
            "span",
            "budget-note",
            formatMoney(status.spent_amount - status.budget_amount, currency) +
              " over"
          )
        );
      } else if (isWarn) {
        foot.append(el("span", "budget-note", "Near limit"));
      } else {
        foot.append(
          el(
            "span",
            "budget-note muted",
            formatMoney(status.remaining, currency) + " left"
          )
        );
      }

      item.append(head, track, foot);
      container.append(item);
    });
  }

  function renderCategoryBreakdown(container, entries, label) {
    if (!entries.length) {
      renderEmptyState(container, "No spending recorded for " + label + ".");
      return;
    }

    // Entries arrive grouped per currency (percentages are shares within one
    // currency), so keep currencies apart and give each group its own pill.
    var codes = [];
    var byCode = {};
    entries.forEach(function (entry) {
      var code = entry.currency || "INR";
      if (!byCode[code]) {
        byCode[code] = [];
        codes.push(code);
      }
      byCode[code].push(entry);
    });

    container.replaceChildren();
    codes.forEach(function (code) {
      var group = el("div", "breakdown-group");
      group.append(currencyPill(code));
      byCode[code].forEach(function (entry) {
        var row = el("div", "breakdown-row");

        var head = el("div", "breakdown-head");
        head.append(
          el("span", "breakdown-label", categoryLabel(entry.category)),
          el(
            "span",
            "breakdown-figures mono",
            formatMoney(entry.amount, code) +
              " · " +
              entry.percentage.toFixed(1) +
              "%"
          )
        );

        var track = el("div", "breakdown-track");
        var fill = el("div", "breakdown-fill");
        fill.style.width = Math.min(entry.percentage, 100) + "%";
        track.append(fill);

        row.append(head, track);
        group.append(row);
      });
      container.append(group);
    });
  }

  function renderUpcomingBills(container, bills) {
    if (!bills.length) {
      renderEmptyState(container, "No bills due soon.");
      return;
    }

    container.replaceChildren();
    bills.forEach(function (bill) {
      var item = el("div", "bill" + (bill.overdue ? " bill-overdue" : ""));

      var head = el("div", "bill-head");
      head.append(el("span", "bill-merchant", bill.merchant || "—"));
      var amount = el("span", "bill-amount");
      amount.append(
        document.createTextNode(formatMoney(bill.amount, bill.currency)),
        currencyPill(bill.currency)
      );
      head.append(amount);

      var foot = el("div", "bill-foot");
      foot.append(
        el(
          "span",
          "bill-due",
          (bill.overdue ? "Was due " : "Due ") +
            formatDay(bill.due_date) +
            (bill.frequency ? " · " + bill.frequency : "")
        )
      );
      if (bill.overdue) {
        foot.append(el("span", "badge badge-overdue", "Overdue"));
      }

      item.append(head, foot);
      container.append(item);
    });
  }

  function renderRecentExpenses(container, items, label) {
    if (!items.length) {
      renderEmptyState(container, "No expenses recorded for " + label + ".");
      return;
    }

    var list = el("ul", "recent-list");
    items.forEach(function (item) {
      var row = el("li", "recent-item");
      row.append(
        el("span", "recent-date mono", formatDay(item.date)),
        el("span", "recent-merchant", item.merchant || "—"),
        el(
          "span",
          "recent-amount mono",
          formatMoney(item.amount, item.currency)
        ),
        currencyPill(item.currency)
      );
      list.append(row);
    });
    container.replaceChildren(list);
  }

  function renderExpenseList(container, items, label, filtersActive) {
    if (!items.length) {
      if (filtersActive) {
        // A filtered-empty month looks nothing like an empty month: say so,
        // and offer the way back.
        var match = el("div", "empty-match");
        match.append(el("p", "muted", "No expenses match your filters."));
        var clear = el("button", "clear-filters", "Clear filters");
        clear.type = "button";
        clear.addEventListener("click", function () {
          resetExpenseFilters();
          loadExpenses();
        });
        match.append(clear);
        container.replaceChildren(match);
        return;
      }
      container.replaceChildren(
        el("p", "muted", "No expenses recorded for " + label + ".")
      );
      return;
    }

    var table = el("table", "expense-table");
    var headRow = el("tr");
    ["Date", "Merchant", "Category", "Amount", "Currency"].forEach(function (name) {
      var cell = el("th", null, name);
      if (name === "Amount") cell.classList.add("align-right");
      headRow.append(cell);
    });
    var head = el("thead");
    head.append(headRow);
    table.append(head);

    var body = el("tbody");
    items.forEach(function (item) {
      var row = el("tr");

      row.append(el("td", "mono", formatDay(item.date)));

      var merchantCell = el("td");
      merchantCell.append(el("span", "merchant", item.merchant || "—"));
      if (item.subcategory) {
        merchantCell.append(el("span", "sub", item.subcategory));
      }
      row.append(merchantCell);

      row.append(el("td", "muted", item.category || "—"));
      row.append(
        el("td", "mono align-right", formatMoney(item.amount, item.currency))
      );

      var currencyCell = el("td");
      currencyCell.append(currencyPill(item.currency));
      row.append(currencyCell);

      body.append(row);
    });
    table.append(body);
    container.replaceChildren(table);
  }

  function apiMonthUrl(path, params) {
    var search = new URLSearchParams(params || {});
    search.set("month", activeMonth());
    return path + "?" + search.toString();
  }

  function fetchMonthData(path, params) {
    return fetch(apiMonthUrl(path, params)).then(function (response) {
      if (response.ok) return response.json();
      // Prefer the server's own explanation (month format, unknown
      // category) over a generic one: this helper serves several 400
      // sources. A non-JSON body (5xx page) falls back to the status.
      return response
        .json()
        .catch(function () {
          return null;
        })
        .then(function (body) {
          throw new Error(
            body && body.detail
              ? body.detail
              : "The server returned " + response.status + "."
          );
        });
    });
  }

  var FILTER_DEBOUNCE_MS = 250;
  var filterTimer = null;
  var expenseRequestToken = 0;
  // The filter controls are static markup, present before this script runs,
  // so one lookup serves both the readers and the listeners below.
  var categoryFilter = document.getElementById("filter-category");
  var merchantFilter = document.getElementById("filter-merchant");

  function expenseFilters() {
    var filters = {};
    if (categoryFilter && categoryFilter.value) {
      filters.category = categoryFilter.value;
    }
    if (merchantFilter && merchantFilter.value.trim()) {
      filters.q = merchantFilter.value.trim();
    }
    return filters;
  }

  function clearFilterTimer() {
    if (filterTimer) {
      clearTimeout(filterTimer);
      filterTimer = null;
    }
  }

  function resetExpenseFilters() {
    if (categoryFilter) categoryFilter.value = "";
    if (merchantFilter) merchantFilter.value = "";
    clearFilterTimer();
  }

  function reloadExpenses() {
    clearFilterTimer();
    loadExpenses();
  }

  function scheduleExpenseReload() {
    clearFilterTimer();
    filterTimer = setTimeout(reloadExpenses, FILTER_DEBOUNCE_MS);
  }

  function loadExpenses() {
    var totalsNode = document.getElementById("totals");
    var expenseListNode = document.getElementById("expense-list");
    if (!totalsNode || !expenseListNode) return;

    // Filter changes and month arrows both fetch; only the newest request
    // may render, or a slow filtered response could land on another month.
    var token = ++expenseRequestToken;
    var filters = expenseFilters();
    var filtersActive = Object.keys(filters).length > 0;

    fetchMonthData("/api/expenses", filters)
      .then(function (data) {
        if (token !== expenseRequestToken) return;
        var label = monthLabel(data.month);
        renderMonthLabels();
        // Totals describe the rows on screen; when a filter matches nothing
        // there is nothing to total, and the list carries the explanation.
        if (filtersActive && !data.items.length) {
          totalsNode.replaceChildren();
        } else {
          renderTotals(totalsNode, data.totals_by_currency || {}, label);
          if (filtersActive) {
            // Mark the amounts as a filtered subtotal so a filtered view
            // can't be read as the whole month's spending.
            totalsNode.prepend(
              el("span", "total-scope", "Matching your filters")
            );
          }
        }
        renderExpenseList(expenseListNode, data.items, label, filtersActive);
      })
      .catch(function (error) {
        if (token !== expenseRequestToken) return;
        totalsNode.replaceChildren();
        expenseListNode.replaceChildren(
          el("p", "error", "Couldn't load expenses. " + error.message)
        );
      });
  }

  if (categoryFilter) {
    categoryFilter.addEventListener("change", reloadExpenses);
  }
  if (merchantFilter) {
    merchantFilter.addEventListener("input", scheduleExpenseReload);
  }

  function loadDashboard() {
    var totalsNode = document.getElementById("dashboard-totals");
    var breakdownNode = document.getElementById("dashboard-breakdown");
    var budgetsNode = document.getElementById("dashboard-budgets");
    var billsNode = document.getElementById("dashboard-bills");
    var recentNode = document.getElementById("dashboard-recent");
    if (!totalsNode || !breakdownNode || !budgetsNode || !billsNode || !recentNode) {
      return;
    }

    fetchMonthData("/api/dashboard")
      .then(function (data) {
        renderMonthLabels();
        var label = monthLabel(data.month);
        renderTotals(totalsNode, data.totals_by_currency || {}, label);
        renderCategoryBreakdown(
          breakdownNode,
          data.category_breakdown || [],
          label
        );
        renderBudgetStatus(budgetsNode, data.budget_statuses || []);
        renderUpcomingBills(billsNode, data.upcoming_bills || []);
        renderRecentExpenses(recentNode, data.recent_expenses || [], label);
      })
      .catch(function (error) {
        var message = "Couldn't load the dashboard. " + error.message;
        [
          totalsNode,
          breakdownNode,
          budgetsNode,
          billsNode,
          recentNode,
        ].forEach(function (node) {
          node.replaceChildren(el("p", "error", message));
        });
      });
  }

  var CHAT_OPEN_KEY = "expense-tracker.chat.open";
  var CHAT_THREAD_KEY = "expense-tracker.chat.thread";
  var CHAT_MESSAGES_KEY = "expense-tracker.chat.messages";
  var CHAT_HISTORY_LIMIT = 200;
  var chatMessages = [];

  function chatStorageGet(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function chatStorageSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      // Storage unavailable (e.g. private mode): the panel still works for
      // this visit, it just won't remember.
    }
  }

  function chatThreadId() {
    var existing = chatStorageGet(CHAT_THREAD_KEY);
    if (existing) return existing;
    var id =
      window.crypto && window.crypto.randomUUID
        ? window.crypto.randomUUID()
        : Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
    chatStorageSet(CHAT_THREAD_KEY, id);
    return id;
  }

  function loadChatMessages() {
    var raw = chatStorageGet(CHAT_MESSAGES_KEY);
    if (!raw) return [];
    try {
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function persistChatMessages() {
    if (chatMessages.length > CHAT_HISTORY_LIMIT) {
      chatMessages = chatMessages.slice(-CHAT_HISTORY_LIMIT);
    }
    chatStorageSet(CHAT_MESSAGES_KEY, JSON.stringify(chatMessages));
  }

  function chatMessageNode(message) {
    var node;
    if (message.role === "error") {
      node = el("p", "chat-error", message.text);
    } else {
      node = el(
        "div",
        "chat-msg chat-msg--" + (message.role === "user" ? "user" : "agent")
      );
      node.append(el("p", "chat-msg-text", message.text));
    }
    return node;
  }

  function chatLog() {
    return document.getElementById("chat-log");
  }

  function appendChatMessage(message) {
    chatMessages.push(message);
    persistChatMessages();
    var log = chatLog();
    if (!log) return;
    var empty = log.querySelector(".chat-empty");
    if (empty) empty.remove();
    log.append(chatMessageNode(message));
    log.scrollTop = log.scrollHeight;
  }

  function renderChatLog() {
    var log = chatLog();
    if (!log || !chatMessages.length) return;
    log.replaceChildren();
    chatMessages.forEach(function (message) {
      log.append(chatMessageNode(message));
    });
    log.scrollTop = log.scrollHeight;
  }

  function applyChatOpenState(open, moveFocus) {
    var panel = document.getElementById("chat-panel");
    var toggle = document.getElementById("chat-toggle");
    if (!panel || !toggle) return;
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (!moveFocus) return;
    if (open) {
      var input = document.getElementById("chat-input");
      if (input) input.focus();
    } else {
      toggle.focus();
    }
  }

  function toggleChat() {
    var panel = document.getElementById("chat-panel");
    if (!panel) return;
    var open = panel.hidden;
    applyChatOpenState(open, true);
    chatStorageSet(CHAT_OPEN_KEY, open ? "1" : "0");
  }

  function sendChatMessage(event) {
    event.preventDefault();
    var input = document.getElementById("chat-input");
    var sendButton = document.getElementById("chat-send");
    if (!input || !sendButton) return;

    var text = (input.value || "").trim();
    if (!text || sendButton.disabled) return;

    appendChatMessage({ role: "user", text: text });
    input.value = "";
    sendButton.disabled = true;

    var log = chatLog();
    var pending = null;
    if (log) {
      pending = el("p", "chat-msg chat-msg--agent chat-pending", "Replying…");
      log.append(pending);
      log.scrollTop = log.scrollHeight;
    }

    fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, thread_id: chatThreadId() }),
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("The server returned " + response.status + ".");
        }
        return response.json();
      })
      .then(function (data) {
        if (pending) pending.remove();
        appendChatMessage({
          role: "agent",
          text: data.response || "The agent didn't reply.",
        });
        renderPage();
      })
      .catch(function (error) {
        if (pending) pending.remove();
        appendChatMessage({
          role: "error",
          text: "Couldn't send your message. " + error.message,
        });
      })
      .finally(function () {
        sendButton.disabled = false;
        input.focus();
      });
  }

  function closeChat() {
    applyChatOpenState(false, true);
    chatStorageSet(CHAT_OPEN_KEY, "0");
  }

  function initChat() {
    var panel = document.getElementById("chat-panel");
    var toggle = document.getElementById("chat-toggle");
    var close = document.getElementById("chat-close");
    var form = document.getElementById("chat-composer");
    if (!panel || !toggle || !close || !form) return;

    chatMessages = loadChatMessages();
    chatThreadId();
    renderChatLog();
    applyChatOpenState(chatStorageGet(CHAT_OPEN_KEY) === "1", false);

    toggle.addEventListener("click", toggleChat);
    close.addEventListener("click", closeChat);
    form.addEventListener("submit", sendChatMessage);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !panel.hidden) closeChat();
    });
  }

  function renderPage() {
    var page = document.body.dataset.page;
    if (page === "dashboard") loadDashboard();
    else if (page === "expenses") loadExpenses();
  }

  function renderMonth() {
    // Filters and search describe one month's view; stepping to another
    // month starts from a clean slate.
    resetExpenseFilters();
    syncNavLinks();
    renderMonthLabels();
    renderPage();
  }

  function goToMonth(month) {
    var url = new URL(window.location.href);
    url.searchParams.set("month", month);
    window.history.pushState({ month: month }, "", url.pathname + url.search);
    renderMonth();
  }

  document.querySelectorAll("[data-month-step]").forEach(function (button) {
    button.addEventListener("click", function () {
      var step = Number(button.getAttribute("data-month-step"));
      goToMonth(shiftMonth(activeMonth(), step));
    });
  });

  window.addEventListener("popstate", renderMonth);

  if (!selectedMonth()) {
    var initialUrl = new URL(window.location.href);
    initialUrl.searchParams.set("month", currentMonth());
    window.history.replaceState(
      { month: currentMonth() },
      "",
      initialUrl.pathname + initialUrl.search
    );
  }

  syncNavLinks();
  renderMonthLabels();
  renderPage();
  initChat();
})();
