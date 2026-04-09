const state = {
  data: null,
  model: localStorage.getItem("booksmart-model") || "gpt-5",
  search: "",
  textbook: null,
  chapter: null,
};

const searchInput = document.getElementById("search-input");
const modelTabs = document.getElementById("model-tabs");
const summaryStrip = document.getElementById("summary-strip");
const breadcrumbs = document.getElementById("breadcrumbs");
const viewRoot = document.getElementById("view-root");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function metricFor(item) {
  return item.metrics[state.model];
}

function round1(value) {
  return Math.round(value * 10) / 10;
}

function parseHash() {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  state.textbook = params.get("textbook");
  const chapterValue = params.get("chapter");
  state.chapter = chapterValue ? Number(chapterValue) : null;
}

function setHash(next) {
  const params = new URLSearchParams();
  if (next.textbook) params.set("textbook", next.textbook);
  if (next.chapter != null) params.set("chapter", String(next.chapter));
  const nextHash = params.toString();
  if (window.location.hash.replace(/^#/, "") === nextHash) {
    parseHash();
    render();
    return;
  }
  window.location.hash = nextHash;
}

function getTextbookByName(name) {
  return state.data.textbooks.find((textbook) => textbook.name === name) || null;
}

function getChapter(textbook, chapterNumber) {
  return textbook.chapters.find((chapter) => chapter.number === chapterNumber) || null;
}

function minChapterMetric(textbook) {
  let minMetric = null;
  for (const chapter of textbook.chapters) {
    const metric = metricFor(chapter);
    if (metric.pct == null) continue;
    if (!minMetric || metric.pct < minMetric.pct) {
      minMetric = { pct: metric.pct, label: chapter.label, n: chapter.n };
    }
  }
  return minMetric;
}

function averageAcrossTextbooks() {
  const values = state.data.textbooks
    .map((textbook) => metricFor(textbook).pct)
    .filter((value) => value != null);
  if (!values.length) return null;
  return round1(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function renderModelTabs() {
  modelTabs.innerHTML = state.data.models
    .map(
      (model) => `
        <button class="model-tab ${model === state.model ? "active" : ""}" data-model="${escapeHtml(model)}">
          ${escapeHtml(model)}
        </button>
      `,
    )
    .join("");

  for (const button of modelTabs.querySelectorAll(".model-tab")) {
    button.addEventListener("click", () => {
      state.model = button.dataset.model;
      localStorage.setItem("booksmart-model", state.model);
      render();
    });
  }
}

function renderSummaryHome(filteredTextbooks) {
  const best = [...filteredTextbooks].sort((a, b) => metricFor(b).pct - metricFor(a).pct)[0];
  const worst = [...filteredTextbooks].sort((a, b) => metricFor(a).pct - metricFor(b).pct)[0];
  const avg = averageAcrossTextbooks();

  summaryStrip.innerHTML = `
    <div class="summary-card card">
      <div class="summary-label">Textbooks</div>
      <div class="summary-value">${filteredTextbooks.length}</div>
      <div class="summary-sub">with Filtered Questions data</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">${escapeHtml(state.model)} average</div>
      <div class="summary-value">${avg == null ? "--" : `${avg}%`}</div>
      <div class="summary-sub">mean textbook accuracy</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">Best textbook</div>
      <div class="summary-value">${best ? `${metricFor(best).pct}%` : "--"}</div>
      <div class="summary-sub">${best ? escapeHtml(best.name) : ""}</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">Lowest textbook</div>
      <div class="summary-value">${worst ? `${metricFor(worst).pct}%` : "--"}</div>
      <div class="summary-sub">${worst ? escapeHtml(worst.name) : ""}</div>
    </div>
  `;
}

function renderSummaryTextbook(textbook) {
  const metric = metricFor(textbook);
  const minChapter = minChapterMetric(textbook);
  summaryStrip.innerHTML = `
    <div class="summary-card card">
      <div class="summary-label">Textbook</div>
      <div class="summary-value">${metric.pct}%</div>
      <div class="summary-sub">${textbook.n.toLocaleString()} questions</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">Chapters</div>
      <div class="summary-value">${textbook.chapters.length}</div>
      <div class="summary-sub">available for drill-down</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">Min chapter</div>
      <div class="summary-value">${minChapter ? `${minChapter.pct}%` : "--"}</div>
      <div class="summary-sub">${minChapter ? escapeHtml(minChapter.label) : ""}</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">Model</div>
      <div class="summary-value">${escapeHtml(state.model)}</div>
      <div class="summary-sub">current accuracy view</div>
    </div>
  `;
}

function renderSummaryChapter(chapter) {
  const metric = metricFor(chapter);
  const sectionMetrics = chapter.sections
    .map((section) => metricFor(section))
    .filter((entry) => entry.pct != null)
    .map((entry) => entry.pct);
  const bestSection = sectionMetrics.length ? Math.max(...sectionMetrics) : null;
  summaryStrip.innerHTML = `
    <div class="summary-card card">
      <div class="summary-label">Chapter</div>
      <div class="summary-value">${metric.pct}%</div>
      <div class="summary-sub">${chapter.n.toLocaleString()} questions</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">Sections</div>
      <div class="summary-value">${chapter.sections.length}</div>
      <div class="summary-sub">${chapter.chapterLevel ? "plus chapter-level questions" : "section rows"}</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">Best section</div>
      <div class="summary-value">${bestSection == null ? "--" : `${bestSection}%`}</div>
      <div class="summary-sub">within this chapter for ${escapeHtml(state.model)}</div>
    </div>
    <div class="summary-card card">
      <div class="summary-label">Model</div>
      <div class="summary-value">${escapeHtml(state.model)}</div>
      <div class="summary-sub">current accuracy view</div>
    </div>
  `;
}

function renderBreadcrumbs(textbook, chapter) {
  const crumbs = [
    `<span class="crumb-link" data-home="true">All textbooks</span>`,
  ];
  if (textbook) {
    crumbs.push(`<span class="crumb-link" data-textbook="${escapeHtml(textbook.name)}">${escapeHtml(textbook.name)}</span>`);
  }
  if (chapter) {
    crumbs.push(`<span class="crumb-current">${escapeHtml(chapter.label)}</span>`);
  }
  breadcrumbs.innerHTML = crumbs.join(`<span class="subtle-note">/</span>`);

  const home = breadcrumbs.querySelector("[data-home]");
  if (home) {
    home.addEventListener("click", () => setHash({}));
  }
  const textbookCrumb = breadcrumbs.querySelector("[data-textbook]");
  if (textbookCrumb) {
    textbookCrumb.addEventListener("click", () => setHash({ textbook: textbook.name }));
  }
}

function barWidth(pctValue) {
  return `width:${Math.max(0, Math.min(100, pctValue || 0))}%`;
}

function chartPanel(title, subtitle, rowsHtml) {
  return `
    <section class="chart-panel card">
      <div class="chart-header">
        <div>
          <h2>${escapeHtml(title)}</h2>
          <p>${escapeHtml(subtitle)}</p>
        </div>
        <div class="chart-scale" aria-hidden="true">
          ${[0, 25, 50, 75, 100]
            .map(
              (tick) => `
                <span class="chart-scale-tick" style="left:${tick}%">
                  ${tick}
                </span>
              `,
            )
            .join("")}
        </div>
      </div>
      <div class="chart-rows">
        ${rowsHtml}
      </div>
    </section>
  `;
}

function textbookRow(textbook) {
  const metric = metricFor(textbook);
  const minChapter = minChapterMetric(textbook);
  return `
    <article class="chart-row clickable-row" data-textbook="${escapeHtml(textbook.name)}">
      <div class="chart-label-block">
        <div class="chart-label">${escapeHtml(textbook.name)}</div>
        <div class="chart-submeta">${textbook.chapters.length} chapters</div>
      </div>
      <div class="chart-bar-cell">
        <div class="chart-bar-track"><div class="chart-bar-fill" style="${barWidth(metric.pct)}"></div></div>
      </div>
      <div class="chart-value">${metric.pct}%</div>
      <div class="chart-meta">${textbook.n.toLocaleString()} q • min ch ${minChapter ? `${minChapter.pct}%` : "--"}</div>
    </article>
  `;
}

function chapterRow(chapter, clickable) {
  const metric = metricFor(chapter);
  return `
    <article class="chart-row ${clickable ? "clickable-row" : ""}" ${clickable ? `data-chapter="${chapter.number}"` : ""}>
      <div class="chart-label-block">
        <div class="chart-label">${escapeHtml(chapter.label)}</div>
        <div class="chart-submeta">${chapter.sections.length ? `${chapter.sections.length} sections` : "chapter-only"}</div>
      </div>
      <div class="chart-bar-cell">
        <div class="chart-bar-track"><div class="chart-bar-fill" style="${barWidth(metric.pct)}"></div></div>
      </div>
      <div class="chart-value">${metric.pct}%</div>
      <div class="chart-meta">${chapter.n.toLocaleString()} q</div>
    </article>
  `;
}

function sectionRow(section, labelSuffix = "section accuracy") {
  const metric = metricFor(section);
  return `
    <article class="chart-row">
      <div class="chart-label-block">
        <div class="chart-label">${escapeHtml(section.title)}</div>
        <div class="chart-submeta">${escapeHtml(labelSuffix)}</div>
      </div>
      <div class="chart-bar-cell">
        <div class="chart-bar-track"><div class="chart-bar-fill" style="${barWidth(metric.pct)}"></div></div>
      </div>
      <div class="chart-value">${metric.pct}%</div>
      <div class="chart-meta">${section.n.toLocaleString()} q</div>
    </article>
  `;
}

function renderHome() {
  const filtered = state.data.textbooks
    .filter((textbook) => textbook.name.toLowerCase().includes(state.search.toLowerCase()))
    .sort((a, b) => metricFor(b).pct - metricFor(a).pct);

  renderSummaryHome(filtered);
  renderBreadcrumbs(null, null);

  if (!filtered.length) {
    viewRoot.innerHTML = `<div class="empty-state card">No textbooks match that search.</div>`;
    return;
  }

  viewRoot.innerHTML = `
    ${chartPanel(
      "Per-textbook accuracy",
      `Use the model selector to switch the ranking. Click any textbook to drill into chapter bars for ${state.model}.`,
      filtered.map(textbookRow).join(""),
    )}
  `;

  for (const row of viewRoot.querySelectorAll("[data-textbook]")) {
    row.addEventListener("click", () => setHash({ textbook: row.dataset.textbook }));
  }
}

function renderTextbook(textbook) {
  renderSummaryTextbook(textbook);
  renderBreadcrumbs(textbook, null);

  const chapters = [...textbook.chapters].sort((a, b) => metricFor(b).pct - metricFor(a).pct);
  viewRoot.innerHTML = `
    ${chartPanel(
      textbook.name,
      `Chapter-level accuracy for ${state.model}. Click a chapter to open section bars when they exist.`,
      chapters.map((chapter) => chapterRow(chapter, chapter.sections.length > 0)).join(""),
    )}
  `;

  for (const row of viewRoot.querySelectorAll("[data-chapter]")) {
    row.addEventListener("click", () =>
      setHash({ textbook: textbook.name, chapter: Number(row.dataset.chapter) }),
    );
  }
}

function renderChapter(textbook, chapter) {
  renderSummaryChapter(chapter);
  renderBreadcrumbs(textbook, chapter);

  const sectionRows = [...chapter.sections]
    .sort((a, b) => metricFor(b).pct - metricFor(a).pct)
    .map((section) => sectionRow(section));
  if (chapter.chapterLevel) {
    sectionRows.push(sectionRow(chapter.chapterLevel, "chapter-level question accuracy"));
  }

  viewRoot.innerHTML = `
    ${
      sectionRows.length
        ? chartPanel(
            chapter.label,
            `Section-level bars for ${state.model} inside ${textbook.name}.`,
            sectionRows.join(""),
          )
        : `<div class="empty-state card">This chapter does not have section rows to drill into.</div>`
    }
  `;
}

function render() {
  if (!state.data) return;

  renderModelTabs();

  const textbook = state.textbook ? getTextbookByName(state.textbook) : null;
  const chapter = textbook && state.chapter != null ? getChapter(textbook, state.chapter) : null;

  if (!textbook) {
    renderHome();
    return;
  }

  if (state.chapter != null && !chapter) {
    setHash({ textbook: textbook.name });
    return;
  }

  if (chapter) {
    renderChapter(textbook, chapter);
    return;
  }

  renderTextbook(textbook);
}

async function loadData() {
  try {
    const response = await fetch("./data/accuracy-site-data.json");
    if (!response.ok) {
      throw new Error(`Failed to load site data: ${response.status}`);
    }
    state.data = await response.json();
    if (!state.data.models.includes(state.model)) {
      state.model = state.data.models[0];
    }
    parseHash();
    render();
  } catch (error) {
    viewRoot.innerHTML = `<div class="empty-state card">${escapeHtml(error.message)}</div>`;
  }
}

searchInput.addEventListener("input", (event) => {
  state.search = event.target.value;
  if (state.textbook || state.chapter != null) {
    setHash({});
    return;
  }
  render();
});

window.addEventListener("hashchange", () => {
  parseHash();
  render();
});

loadData();
