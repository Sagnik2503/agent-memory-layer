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

  function syncNavLinks() {
    var month = selectedMonth() || currentMonth();
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

  function renderTotals(container, totals) {
    container.replaceChildren();
    Object.keys(totals).forEach(function (currency) {
      var item = el("span", "total");
      item.append(
        currencyPill(currency),
        document.createTextNode(formatMoney(totals[currency], currency))
      );
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

  function loadExpenses() {
    var raw = monthParam();
    var month = raw || currentMonth();
    var monthNode = document.getElementById("month-label");
    var totalsNode = document.getElementById("totals");
    var expenseListNode = document.getElementById("expense-list");
    if (!monthNode || !totalsNode || !expenseListNode) return;

    if (MONTH_PATTERN.test(month)) {
      monthNode.textContent = monthLabel(month);
    }

    fetch("/api/expenses?month=" + encodeURIComponent(month))
      .then(function (response) {
        if (!response.ok) {
          throw new Error("The month should look like 2026-09.");
        }
        return response.json();
      })
      .then(function (data) {
        var label = monthLabel(data.month);
        monthNode.textContent = label;
        renderTotals(totalsNode, data.totals_by_currency || {});
        renderExpenseList(expenseListNode, data.items, label);
      })
      .catch(function (error) {
        totalsNode.replaceChildren();
        expenseListNode.replaceChildren(
          el("p", "error", "Couldn't load expenses. " + error.message)
        );
      });
  }

  syncNavLinks();
  if (document.body.dataset.page === "expenses") {
    loadExpenses();
  }
})();
