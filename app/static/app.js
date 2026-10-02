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

  function renderTotals(container, totals, label) {
    var currencies = Object.keys(totals);
    if (!currencies.length) {
      container.replaceChildren(
        el("p", "muted empty-state", "No spending recorded for " + label + ".")
      );
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

  function budgetLabel(category) {
    return category ? category.replace(/_/g, " ") : "Overall";
  }

  function renderBudgetStatus(container, statuses) {
    if (!statuses.length) {
      container.replaceChildren(el("p", "muted empty-state", "No budgets set."));
      return;
    }

    container.replaceChildren();
    statuses.forEach(function (status) {
      var percent = Math.max(0, status.percentage_used);
      var isOver = !!status.is_over_budget;
      var isWarn = !isOver && percent >= BUDGET_WARNING_PERCENT;
      var currency = status.currency;
      var label = budgetLabel(status.category);

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

  function renderExpenseList(container, items, label) {
    if (!items.length) {
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

  function apiMonthUrl(path) {
    return path + "?month=" + encodeURIComponent(activeMonth());
  }

  function fetchMonthData(path) {
    return fetch(apiMonthUrl(path)).then(function (response) {
      if (!response.ok) {
        throw new Error(
          response.status === 400
            ? "The month should look like 2026-09."
            : "The server returned " + response.status + "."
        );
      }
      return response.json();
    });
  }

  function loadExpenses() {
    var totalsNode = document.getElementById("totals");
    var expenseListNode = document.getElementById("expense-list");
    if (!totalsNode || !expenseListNode) return;

    fetchMonthData("/api/expenses")
      .then(function (data) {
        var label = monthLabel(data.month);
        renderMonthLabels();
        renderTotals(totalsNode, data.totals_by_currency || {}, label);
        renderExpenseList(expenseListNode, data.items, label);
      })
      .catch(function (error) {
        totalsNode.replaceChildren();
        expenseListNode.replaceChildren(
          el("p", "error", "Couldn't load expenses. " + error.message)
        );
      });
  }

  function loadDashboard() {
    var totalsNode = document.getElementById("dashboard-totals");
    var budgetsNode = document.getElementById("dashboard-budgets");
    if (!totalsNode || !budgetsNode) return;

    fetchMonthData("/api/dashboard")
      .then(function (data) {
        renderMonthLabels();
        renderTotals(
          totalsNode,
          data.totals_by_currency || {},
          monthLabel(data.month)
        );
        renderBudgetStatus(budgetsNode, data.budget_statuses || []);
      })
      .catch(function (error) {
        var message = "Couldn't load the dashboard. " + error.message;
        totalsNode.replaceChildren(el("p", "error", message));
        budgetsNode.replaceChildren(el("p", "error", message));
      });
  }

  function renderPage() {
    var page = document.body.dataset.page;
    if (page === "dashboard") loadDashboard();
    else if (page === "expenses") loadExpenses();
  }

  function renderMonth() {
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
})();
