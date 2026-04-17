const STEM_TEXTBOOKS = new Set([
  "Prealgebra 2e",
  "Elementary Algebra 2e",
  "Intermediate Algebra 2e",
  "College Algebra",
  "Algebra and Trig 2e",
  "Precalc",
  "Calc V1",
  "Calc V2",
  "Calc V3",
  "Statistics High School",
  "Stats 2e",
  "Business Stats",
  "College Physics 2e",
  "University Physics V1",
  "University Physics V2",
  "University Physics V3",
  "Chem 2e",
  "Microbiology",
]);

const CATEGORY_ORDER = [
  "Accounting and Finance",
  "Algebra and Trigonometry",
  "American Government",
  "Biology",
  "Business Law and Ethics",
  "Calculus",
  "Chemistry",
  "College Algebra",
  "Developmental Math",
  "Physics",
  "Precalculus",
  "Sociology",
  "Statistics",
  "U.S. History",
  "Other",
];

const TEXTBOOK_TO_CATEGORY = {
  "Accounting V1": "Accounting and Finance",
  "Accounting V2": "Accounting and Finance",
  "Algebra and Trig 2e": "Algebra and Trigonometry",
  "American Gov 3e": "American Government",
  "Business Ethics": "Business Law and Ethics",
  "Business Law": "Business Law and Ethics",
  "Business Stats": "Statistics",
  "Calc V1": "Calculus",
  "Calc V2": "Calculus",
  "Calc V3": "Calculus",
  "Chem 2e": "Chemistry",
  "College Algebra": "College Algebra",
  "College Physics 2e": "Physics",
  "Elementary Algebra 2e": "Developmental Math",
  "Intellectual Property": "Business Law and Ethics",
  "Intermediate Algebra 2e": "Developmental Math",
  "Microbiology": "Biology",
  "Prealgebra 2e": "Developmental Math",
  "Precalc": "Precalculus",
  "Sociology": "Sociology",
  "Statistics High School": "Statistics",
  "Stats 2e": "Statistics",
  "US History": "U.S. History",
  "University Physics V1": "Physics",
  "University Physics V2": "Physics",
  "University Physics V3": "Physics",
};

const BAR_COLORS = [
  "#7c9cff",
  "#34d399",
  "#f59e0b",
  "#f87171",
  "#a78bfa",
  "#22d3ee",
  "#fb7185",
  "#84cc16",
];

const state = {
  data: null,
  selectedModels: [],
  search: "",
  explore: {
    level: "textbooks",
    textbook: null,
    chapter: null,
  },
  view: {
    level: "overall",
    tier: null,
    category: null,
    textbook: null,
    chapter: null,
  },
};

const modelTabs = document.getElementById("model-tabs");
const breadcrumbs = document.getElementById("breadcrumbs");
const viewRoot = document.getElementById("view-root");
const exploreRoot = document.getElementById("explore-root");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function tierForTextbook(name) {
  return STEM_TEXTBOOKS.has(name) ? "STEM" : "Non-STEM";
}

function categoryForTextbook(name) {
  return TEXTBOOK_TO_CATEGORY[name] || "Other";
}

function categorySort(a, b) {
  return CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b) || a.localeCompare(b);
}

function round1(value) {
  return Math.round(value * 10) / 10;
}

function getTextbookByName(name) {
  return state.data.textbooks.find((book) => book.name === name) || null;
}

function getChapter(textbook, chapterNumber) {
  return textbook.chapters.find((chapter) => chapter.number === chapterNumber) || null;
}

function sectionDisplayTitle(section) {
  const id = String(section.id || "").trim();
  const title = String(section.title || "").trim();
  if (!id) return title;
  if (!title) return id;

  const escapedId = id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const dedupedTitle = title.replace(new RegExp(`^${escapedId}(?:\\s*[-:]\\s*)?`, "i"), "").trim();
  return dedupedTitle ? `${id} ${dedupedTitle}` : id;
}

function aggregateMetrics(items) {
  const byModel = {};
  for (const model of state.data.models) {
    let correct = 0;
    let n = 0;
    for (const item of items) {
      const metric = item.metrics[model];
      if (!metric || metric.n <= 0) continue;
      correct += metric.correct;
      n += metric.n;
    }
    byModel[model] = {
      correct,
      n,
      pct: n > 0 ? round1((100 * correct) / n) : null,
    };
  }
  return byModel;
}

function parseHash() {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const level = params.get("level") || "overall";
  const chapterValue = params.get("chapter");

  state.view = {
    level,
    tier: params.get("tier"),
    category: params.get("category"),
    textbook: params.get("textbook"),
    chapter: chapterValue == null ? null : Number(chapterValue),
  };
}

function setHash(view) {
  const params = new URLSearchParams();
  params.set("level", view.level);
  if (view.tier) params.set("tier", view.tier);
  if (view.category) params.set("category", view.category);
  if (view.textbook) params.set("textbook", view.textbook);
  if (view.chapter != null) params.set("chapter", String(view.chapter));
  const hash = params.toString();
  if (window.location.hash.replace(/^#/, "") === hash) {
    parseHash();
    render();
    return;
  }
  window.location.hash = hash;
}

function scrollCardToViewportTop(selector) {
  const target = document.querySelector(selector);
  if (!target) return;
  const top = window.scrollY + target.getBoundingClientRect().top;
  window.scrollTo({ top, behavior: "smooth" });
}

function navigateWithScroll(view, scrollSelector = "#view-root .plot-card") {
  setHash(view);
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      scrollCardToViewportTop(scrollSelector);
    });
  });
}

function renderModelSelector() {
  modelTabs.innerHTML = state.data.models
    .map((model, idx) => {
      const checked = state.selectedModels.includes(model) ? "checked" : "";
      return `
        <label class="model-check" title="${escapeHtml(model)}">
          <input type="checkbox" data-model="${escapeHtml(model)}" ${checked} />
          <span class="model-dot" style="background:${BAR_COLORS[idx % BAR_COLORS.length]}"></span>
          <span>${escapeHtml(model)}</span>
        </label>
      `;
    })
    .join("");

  for (const input of modelTabs.querySelectorAll("input[type='checkbox']")) {
    input.addEventListener("change", () => {
      const model = input.dataset.model;
      const next = new Set(state.selectedModels);
      if (input.checked) {
        next.add(model);
      } else {
        next.delete(model);
      }
      if (next.size === 0) {
        input.checked = true;
        return;
      }
      state.selectedModels = state.data.models.filter((entry) => next.has(entry));
      render();
    });
  }
}

function makeBreadcrumbs() {
  const crumbs = [
    {
      label: "Overall",
      view: { level: "overall", tier: null, category: null, textbook: null, chapter: null },
    },
  ];

  if (state.view.level === "tier") {
    return crumbs;
  }

  if (["category", "textbook", "chapter", "section"].includes(state.view.level) && state.view.tier) {
    crumbs.push({
      label: state.view.tier,
      view: { level: "tier", tier: null, category: null, textbook: null, chapter: null },
    });
  }

  if (["textbook", "chapter", "section"].includes(state.view.level) && state.view.category) {
    crumbs.push({
      label: state.view.category,
      view: { level: "category", tier: state.view.tier, category: null, textbook: null, chapter: null },
    });
  }

  if (["chapter", "section"].includes(state.view.level) && state.view.textbook) {
    crumbs.push({
      label: state.view.textbook,
      view: {
        level: "textbook",
        tier: state.view.tier,
        category: state.view.category,
        textbook: null,
        chapter: null,
      },
    });
  }

  if (state.view.level === "section" && state.view.textbook && state.view.chapter != null) {
    crumbs.push({
      label: `Chapter ${state.view.chapter}`,
      view: {
        level: "chapter",
        tier: state.view.tier,
        category: state.view.category,
        textbook: state.view.textbook,
        chapter: null,
      },
    });
  }

  return crumbs;
}

function renderBreadcrumbs() {
  const crumbs = makeBreadcrumbs();
  breadcrumbs.innerHTML = crumbs
    .map(
      (crumb, idx) => `
        <button class="crumb-button ${idx === crumbs.length - 1 ? "is-current" : ""}" data-crumb="${idx}">
          ${escapeHtml(crumb.label)}
        </button>
      `,
    )
    .join(`<span class="subtle-note">/</span>`);

  for (const button of breadcrumbs.querySelectorAll("[data-crumb]")) {
    button.addEventListener("click", () => {
      const idx = Number(button.dataset.crumb);
      setHash(crumbs[idx].view);
    });
  }
}

function buildGroups() {
  const filteredTextbooks = state.data.textbooks;

  if (state.view.level === "overall") {
    return {
      title: "All Textbooks",
      groups: [
        {
          id: "all",
          label: "All textbooks",
          metrics: aggregateMetrics(filteredTextbooks),
          n: filteredTextbooks.reduce((sum, book) => sum + book.n, 0),
          canExpand: true,
          nextView: { level: "tier", tier: null, category: null, textbook: null, chapter: null },
        },
      ],
    };
  }

  if (state.view.level === "tier") {
    const stem = filteredTextbooks.filter((book) => tierForTextbook(book.name) === "STEM");
    const nonStem = filteredTextbooks.filter((book) => tierForTextbook(book.name) === "Non-STEM");
    return {
      title: "STEM vs Non-STEM",
      groups: [
        {
          id: "stem",
          label: "STEM",
          metrics: aggregateMetrics(stem),
          n: stem.reduce((sum, book) => sum + book.n, 0),
          canExpand: true,
          nextView: { level: "category", tier: "STEM", category: null, textbook: null, chapter: null },
        },
        {
          id: "nonstem",
          label: "Non-STEM",
          metrics: aggregateMetrics(nonStem),
          n: nonStem.reduce((sum, book) => sum + book.n, 0),
          canExpand: true,
          nextView: { level: "category", tier: "Non-STEM", category: null, textbook: null, chapter: null },
        },
      ],
    };
  }

  if (state.view.level === "category") {
    const textbooks = filteredTextbooks.filter((book) => tierForTextbook(book.name) === state.view.tier);
    const byCategory = {};
    for (const book of textbooks) {
      const category = categoryForTextbook(book.name);
      if (!byCategory[category]) byCategory[category] = [];
      byCategory[category].push(book);
    }

    const categories = Object.keys(byCategory).sort(categorySort);
    return {
      title: `${state.view.tier} Categories`,
      groups: categories.map((category) => {
        const books = byCategory[category];
        return {
          id: category,
          label: category,
          metrics: aggregateMetrics(books),
          n: books.reduce((sum, book) => sum + book.n, 0),
          canExpand: true,
          nextView: {
            level: "textbook",
            tier: state.view.tier,
            category,
            textbook: null,
            chapter: null,
          },
        };
      }),
    };
  }

  if (state.view.level === "textbook") {
    const textbooks = filteredTextbooks
      .filter((book) => tierForTextbook(book.name) === state.view.tier)
      .filter((book) => categoryForTextbook(book.name) === state.view.category)
      .sort((a, b) => b.metrics[state.selectedModels[0]].pct - a.metrics[state.selectedModels[0]].pct);

    return {
      title: `${state.view.category} Textbooks`,
      groups: textbooks.map((book) => ({
        id: book.name,
        label: book.name,
        metrics: book.metrics,
        n: book.n,
        canExpand: true,
        nextView: {
          level: "chapter",
          tier: state.view.tier,
          category: state.view.category,
          textbook: book.name,
          chapter: null,
        },
      })),
    };
  }

  if (state.view.level === "chapter") {
    const textbook = getTextbookByName(state.view.textbook);
    if (!textbook) {
      return { title: "Missing textbook", groups: [] };
    }

    return {
      title: `${textbook.name} Chapters`,
      groups: [...textbook.chapters]
        .sort((a, b) => a.number - b.number)
        .map((chapter) => ({
          id: String(chapter.number),
          label: chapter.label,
          metrics: chapter.metrics,
          n: chapter.n,
          canExpand: chapter.sections.length > 0,
          nextView: chapter.sections.length
            ? {
                level: "section",
                tier: state.view.tier,
                category: state.view.category,
                textbook: textbook.name,
                chapter: chapter.number,
              }
            : null,
        })),
    };
  }

  if (state.view.level === "section") {
    const textbook = getTextbookByName(state.view.textbook);
    const chapter = textbook ? getChapter(textbook, state.view.chapter) : null;
    if (!textbook || !chapter) {
      return { title: "Missing chapter", groups: [] };
    }

    const sectionGroups = chapter.sections.map((section) => ({
      id: section.id,
      label: sectionDisplayTitle(section),
      metrics: section.metrics,
      n: section.n,
      canExpand: false,
      nextView: null,
    }));

    if (chapter.chapterLevel) {
      sectionGroups.push({
        id: "chapter-level",
        label: "Chapter-level questions",
        metrics: chapter.chapterLevel.metrics,
        n: chapter.chapterLevel.n,
        canExpand: false,
        nextView: null,
      });
    }

    return {
      title: `${chapter.label} Subchapters`,
      groups: sectionGroups,
    };
  }

  return { title: "View", groups: [] };
}

function getExplorePath() {
  const path = [{ label: "Textbooks", level: "textbooks" }];
  if (state.explore.level === "chapters" || state.explore.level === "sections") {
    path.push({ label: state.explore.textbook, level: "chapters" });
  }
  if (state.explore.level === "sections") {
    path.push({ label: `Chapter ${state.explore.chapter}`, level: "sections" });
  }
  return path;
}

function exploreMiniBars(metrics) {
  return state.selectedModels
    .map((selectedModel) => {
      const selectedPct = metrics[selectedModel]?.pct ?? 0;
      return `
        <div class="explore-mini-row">
          <span class="explore-mini-label">${escapeHtml(selectedModel)}</span>
          <div class="explore-mini-track">
            <div class="explore-mini-fill" style="width:${selectedPct}%; background:${modelColor(selectedModel)}"></div>
          </div>
          <span class="explore-mini-value">${selectedPct}%</span>
        </div>
      `;
    })
    .join("");
}

function getExploreRows(primaryModel) {
  const level = state.explore.level;
  if (level === "textbooks") {
    const searchLower = state.search.trim().toLowerCase();
    return state.data.textbooks
      .filter((book) => !searchLower || book.name.toLowerCase().includes(searchLower))
      .sort((a, b) => (b.metrics[primaryModel]?.pct ?? -1) - (a.metrics[primaryModel]?.pct ?? -1))
      .map((book) => ({
        title: book.name,
        subtitle: `${tierForTextbook(book.name)} • ${categoryForTextbook(book.name)} • ${book.n.toLocaleString()} q`,
        score: `${book.metrics[primaryModel]?.pct ?? "--"}%`,
        metrics: book.metrics,
        clickable: true,
        next: { level: "chapters", textbook: book.name, chapter: null },
      }));
  }

  const textbook = getTextbookByName(state.explore.textbook);
  if (!textbook) {
    state.explore = { level: "textbooks", textbook: null, chapter: null };
    return [];
  }

  if (level === "chapters") {
    return [...textbook.chapters]
      .sort((a, b) => a.number - b.number)
      .map((chapter) => ({
        title: chapter.label,
        subtitle: `${chapter.sections.length ? `${chapter.sections.length} subchapters` : "no subchapters"} • ${chapter.n.toLocaleString()} q`,
        score: `${chapter.metrics[primaryModel]?.pct ?? "--"}%`,
        metrics: chapter.metrics,
        clickable: chapter.sections.length > 0,
        next: chapter.sections.length
          ? { level: "sections", textbook: textbook.name, chapter: chapter.number }
          : null,
      }));
  }

  const chapter = getChapter(textbook, state.explore.chapter);
  if (!chapter) {
    state.explore = { level: "chapters", textbook: textbook.name, chapter: null };
    return [];
  }

  const sectionRows = chapter.sections.map((section) => ({
    title: sectionDisplayTitle(section),
    subtitle: `${section.n.toLocaleString()} q`,
    score: `${section.metrics[primaryModel]?.pct ?? "--"}%`,
    metrics: section.metrics,
    clickable: false,
    next: null,
  }));

  if (chapter.chapterLevel) {
    sectionRows.push({
      title: "Chapter-level questions",
      subtitle: `${chapter.chapterLevel.n.toLocaleString()} q`,
      score: `${chapter.chapterLevel.metrics[primaryModel]?.pct ?? "--"}%`,
      metrics: chapter.chapterLevel.metrics,
      clickable: false,
      next: null,
    });
  }
  return sectionRows;
}

function renderExploreList() {
  const primaryModel = state.selectedModels[0] || state.data.models[0];
  const exploreSub = exploreRoot.querySelector(".explore-sub");
  const exploreList = exploreRoot.querySelector(".explore-list");
  const explorePath = exploreRoot.querySelector(".explore-path");
  if (!exploreSub || !exploreList || !explorePath) return;

  const path = getExplorePath();
  explorePath.innerHTML = path
    .map(
      (crumb, idx) => `
        <button class="explore-crumb ${idx === path.length - 1 ? "is-current" : ""}" data-crumb-index="${idx}">
          ${escapeHtml(crumb.label)}
        </button>
      `,
    )
    .join(`<span class="subtle-note">/</span>`);

  for (const button of explorePath.querySelectorAll("[data-crumb-index]")) {
    button.addEventListener("click", () => {
      const idx = Number(button.dataset.crumbIndex);
      const targetLevel = path[idx].level;
      if (targetLevel === "textbooks") {
        state.explore = { level: "textbooks", textbook: null, chapter: null };
      } else if (targetLevel === "chapters") {
        state.explore = { level: "chapters", textbook: state.explore.textbook, chapter: null };
      }
      renderExploreList();
    });
  }

  const rows = getExploreRows(primaryModel);
  const sectionLabel =
    state.explore.level === "textbooks"
      ? `${rows.length} result${rows.length === 1 ? "" : "s"} • sorted by ${escapeHtml(primaryModel)}`
      : state.explore.level === "chapters"
        ? `${rows.length} chapter${rows.length === 1 ? "" : "s"} • sorted by chapter order`
        : `${rows.length} subchapter row${rows.length === 1 ? "" : "s"}`;
  exploreSub.innerHTML = sectionLabel;

  exploreList.innerHTML = rows.length
    ? rows
        .map(
          (row, idx) => `
            <article class="explore-row ${row.clickable ? "is-clickable" : ""}" data-row-index="${idx}">
              <div class="explore-name">${escapeHtml(row.title)}</div>
              <div class="explore-meta">${escapeHtml(row.subtitle)}</div>
              <div class="explore-bars">${exploreMiniBars(row.metrics)}</div>
              <div class="explore-score">${row.score}</div>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state">No rows available at this level.</div>`;

  for (const rowEl of exploreList.querySelectorAll("[data-row-index]")) {
    rowEl.addEventListener("click", () => {
      const row = rows[Number(rowEl.dataset.rowIndex)];
      if (!row || !row.next) return;
      state.explore = row.next;
      renderExploreList();
      scrollCardToViewportTop("#explore-root .explore-card");
    });
  }
}

function renderExplore() {
  if (!exploreRoot.querySelector(".explore-card")) {
    exploreRoot.innerHTML = `
      <section class="explore-card card">
        <div class="explore-head">
          <h3>Explore Textbooks</h3>
          <input id="explore-search" type="search" placeholder="Search textbooks..." />
        </div>
        <div class="explore-path"></div>
        <div class="explore-sub"></div>
        <div class="explore-list"></div>
      </section>
    `;

    const exploreSearch = document.getElementById("explore-search");
    exploreSearch.addEventListener("input", (event) => {
      state.search = event.target.value;
      state.explore = { level: "textbooks", textbook: null, chapter: null };
      renderExploreList();
    });
  }

  const exploreSearch = document.getElementById("explore-search");
  const textbooksLevel = state.explore.level === "textbooks";
  exploreSearch.disabled = !textbooksLevel;
  if (document.activeElement !== exploreSearch) {
    exploreSearch.value = state.search;
  }
  renderExploreList();
}

function modelColor(model) {
  const idx = state.data.models.indexOf(model);
  return BAR_COLORS[idx % BAR_COLORS.length];
}

function legendHtml() {
  return `
    <div class="plot-legend">
      ${state.selectedModels
        .map(
          (model) => `
            <span class="legend-item">
              <span class="legend-dot" style="background:${modelColor(model)}"></span>
              ${escapeHtml(model)}
            </span>
          `,
        )
        .join("")}
    </div>
  `;
}

function groupBarsHtml(group) {
  return `
    <article class="group-column ${group.canExpand ? "is-clickable" : ""}" ${group.canExpand ? `data-expand-group="${escapeHtml(group.id)}"` : ""}>
      <div class="bars-wrap">
        <div class="bars-cluster">
          ${state.selectedModels
            .map((model) => {
              const metric = group.metrics[model];
              const pct = metric && metric.pct != null ? metric.pct : 0;
              return `
                <div class="bar-holder">
                  <div class="bar-value">${pct}%</div>
                  <div class="bar-area">
                    <div class="bar" style="height:${pct}%; background:${modelColor(model)}" title="${escapeHtml(model)}: ${pct}%"></div>
                  </div>
                </div>
              `;
            })
            .join("")}
        </div>
      </div>
      <div class="x-meta">${group.n.toLocaleString()} questions</div>
      <div class="x-label">${escapeHtml(group.label)}</div>
    </article>
  `;
}

function renderPlot() {
  const payload = buildGroups();

  if (!payload.groups.length) {
    viewRoot.innerHTML = `<div class="empty-state card">No data at this level for the current filters.</div>`;
    return;
  }

  viewRoot.innerHTML = `
    <section class="plot-card card">
      <div class="plot-head">
        <div>
          <h2>${escapeHtml(payload.title)}</h2>
          <div class="plot-hint">Click a cluster to expand</div>
        </div>
        ${legendHtml()}
      </div>
      <div class="plot-columns">
        ${payload.groups.map((group) => groupBarsHtml(group)).join("")}
      </div>
    </section>
  `;

  for (const cluster of viewRoot.querySelectorAll("[data-expand-group]")) {
    cluster.addEventListener("click", () => {
      const group = payload.groups.find((entry) => entry.id === cluster.dataset.expandGroup);
      if (!group || !group.nextView) return;
      let nextView = group.nextView;

      // Auto-skip textbook level when a category has only one textbook.
      if (nextView.level === "textbook" && nextView.tier && nextView.category) {
        const textbooksInCategory = state.data.textbooks.filter(
          (book) =>
            tierForTextbook(book.name) === nextView.tier &&
            categoryForTextbook(book.name) === nextView.category,
        );
        if (textbooksInCategory.length === 1) {
          nextView = {
            level: "chapter",
            tier: nextView.tier,
            category: nextView.category,
            textbook: textbooksInCategory[0].name,
            chapter: null,
          };
        }
      }

      navigateWithScroll(nextView, "#view-root .plot-card");
    });
  }
}

function normalizeView() {
  if (state.view.level === "overall") return false;

  if (state.view.level === "tier") return false;

  if (state.view.level === "category" && !state.view.tier) {
    setHash({ level: "tier", tier: null, category: null, textbook: null, chapter: null });
    return true;
  }

  if (state.view.level === "textbook" && (!state.view.tier || !state.view.category)) {
    setHash({ level: "category", tier: state.view.tier || "STEM", category: null, textbook: null, chapter: null });
    return true;
  }

  if (state.view.level === "chapter" && !state.view.textbook) {
    setHash({
      level: "textbook",
      tier: state.view.tier,
      category: state.view.category,
      textbook: null,
      chapter: null,
    });
    return true;
  }

  if (state.view.level === "section" && (!state.view.textbook || state.view.chapter == null)) {
    setHash({
      level: "chapter",
      tier: state.view.tier,
      category: state.view.category,
      textbook: state.view.textbook,
      chapter: null,
    });
    return true;
  }
  return false;
}

function render() {
  if (!state.data) return;
  if (normalizeView()) return;
  renderModelSelector();
  renderBreadcrumbs();
  renderPlot();
  renderExplore();
}

async function loadData() {
  try {
    const response = await fetch(`./data/accuracy-site-data.json?v=${Date.now()}`);
    if (!response.ok) {
      throw new Error(`Failed to load site data: ${response.status}`);
    }
    state.data = await response.json();
    state.selectedModels = [...state.data.models];
    parseHash();
    render();
  } catch (error) {
    viewRoot.innerHTML = `<div class="empty-state card">${escapeHtml(error.message)}</div>`;
  }
}

window.addEventListener("hashchange", () => {
  parseHash();
  render();
});

loadData();
