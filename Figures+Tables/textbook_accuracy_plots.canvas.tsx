type Row = {
  textbook: string;
  model: string;
  textbookQuestions: number;
  avg: number;
  minChapter: number;
};

const MODEL_ORDER = ["o3", "deepseek-chat", "gemini-2.5-pro", "o4-mini", "gpt-5"];

const MODEL_COLORS: Record<string, string> = {
  o3: "#2563eb",
  "deepseek-chat": "#dc2626",
  "gemini-2.5-pro": "#7c3aed",
  "o4-mini": "#ea580c",
  "gpt-5": "#059669",
};

const GRADE_BANDS = [
  { label: "F", threshold: 0 },
  { label: "D-", threshold: 60 },
  { label: "D", threshold: 63 },
  { label: "D+", threshold: 67 },
  { label: "C-", threshold: 70 },
  { label: "C", threshold: 73 },
  { label: "C+", threshold: 77 },
  { label: "B-", threshold: 80 },
  { label: "B", threshold: 83 },
  { label: "B+", threshold: 87 },
  { label: "A-", threshold: 90 },
  { label: "A", threshold: 93 },
  { label: "A+", threshold: 97 },
];

const CSV_DATA = `textbook,model,textbook_questions_n,avg_accuracy_pct,min_chapter_accuracy_pct,min_chapter_number,min_chapter_label,min_chapter_questions_n
Accounting V1,o3,318,95.6,88.9,4,Chapter 4: Job Order Costing,18
Accounting V1,deepseek-chat,318,89.3,81.5,7,Chapter 7: Budgeting,27
Accounting V1,gemini-2.5-pro,318,94.3,87.0,14,Chapter 14: Corporation Accounting,23
Accounting V1,o4-mini,318,93.7,82.6,14,Chapter 14: Corporation Accounting,23
Accounting V1,gpt-5,318,97.2,92.0,9,Chapter 9: Responsibility Accounting and Decentralization,25
Accounting V2,o3,230,96.5,85.7,10,Chapter 10: Short-Term Decision-Making,14
Accounting V2,deepseek-chat,230,88.7,80.0,11,Chapter 11: Capital Budgeting Decisions,20
Accounting V2,gemini-2.5-pro,230,93.9,70.0,11,Chapter 11: Capital Budgeting Decisions,20
Accounting V2,o4-mini,230,94.8,80.0,7,Chapter 7: Budgeting,15
Accounting V2,gpt-5,230,94.8,80.0,11,Chapter 11: Capital Budgeting Decisions,20
Algebra and Trig 2e,o3,3092,96.2,89.1,4,Chapter 4: Linear Functions,128
Algebra and Trig 2e,deepseek-chat,3092,90.0,76.4,8,Chapter 8: Periodic Functions,89
Algebra and Trig 2e,gemini-2.5-pro,3092,95.2,89.1,4,Chapter 4: Linear Functions,128
Algebra and Trig 2e,o4-mini,3092,95.5,89.1,4,Chapter 4: Linear Functions,128
Algebra and Trig 2e,gpt-5,3092,95.9,90.6,4,Chapter 4: Linear Functions,128
American Gov 3e,o3,161,93.8,77.8,17,Chapter 17,9
American Gov 3e,deepseek-chat,161,87.6,66.7,1,Chapter 1,6
American Gov 3e,gemini-2.5-pro,161,91.3,75.0,12,Chapter 12,8
American Gov 3e,o4-mini,161,92.5,66.7,1,Chapter 1,6
American Gov 3e,gpt-5,161,88.8,75.0,16,Chapter 16,8
Business Ethics,o3,193,91.7,83.3,6,Chapter 6,18
Business Ethics,deepseek-chat,193,87.6,69.2,3,Chapter 3,13
Business Ethics,gemini-2.5-pro,193,90.7,80.0,7,Chapter 7,25
Business Ethics,o4-mini,193,89.6,76.0,7,Chapter 7,25
Business Ethics,gpt-5,193,87.0,72.0,7,Chapter 7,25
Business Law,o3,79,94.9,75.0,11,Chapter 11,8
Business Law,deepseek-chat,79,91.1,75.0,11,Chapter 11,8
Business Law,gemini-2.5-pro,79,94.9,80.0,13,Chapter 13,5
Business Law,o4-mini,79,91.1,62.5,11,Chapter 11,8
Business Law,gpt-5,79,92.4,75.0,11,Chapter 11,8
Business Stats,o3,377,84.4,56.8,6,Chapter 6,37
Business Stats,deepseek-chat,377,75.6,51.4,6,Chapter 6,37
Business Stats,gemini-2.5-pro,377,82.2,48.6,6,Chapter 6,37
Business Stats,o4-mini,377,85.9,54.1,6,Chapter 6,37
Business Stats,gpt-5,377,84.9,59.5,6,Chapter 6,37
Calc V1,o3,1059,94.3,89.0,2,Chapter 2: Vectors in Space,109
Calc V1,deepseek-chat,1059,84.9,78.0,2,Chapter 2: Vectors in Space,109
Calc V1,gemini-2.5-pro,1059,93.0,85.8,6,Chapter 6: Vector Calculus,162
Calc V1,o4-mini,1059,92.9,88.3,6,Chapter 6: Vector Calculus,162
Calc V1,gpt-5,1059,94.7,87.7,6,Chapter 6: Vector Calculus,162
Calc V2,o3,1219,93.9,86.1,4,Chapter 4: Differentiation of Functions of Several Variables,108
Calc V2,deepseek-chat,1219,88.4,77.8,4,Chapter 4: Differentiation of Functions of Several Variables,108
Calc V2,gemini-2.5-pro,1219,91.8,85.2,4,Chapter 4: Differentiation of Functions of Several Variables,108
Calc V2,o4-mini,1219,91.6,84.3,4,Chapter 4: Differentiation of Functions of Several Variables,108
Calc V2,gpt-5,1219,93.2,82.4,4,Chapter 4: Differentiation of Functions of Several Variables,108
Calc V3,o3,1108,92.5,88.3,7,Chapter 7: Second-Order Differential Equations,77
Calc V3,deepseek-chat,1108,82.5,69.3,3,Chapter 3: Vector-Valued Functions,88
Calc V3,gemini-2.5-pro,1108,92.8,87.5,3,Chapter 3: Vector-Valued Functions,88
Calc V3,o4-mini,1108,94.0,88.6,3,Chapter 3: Vector-Valued Functions,88
Calc V3,gpt-5,1108,93.3,90.9,3,Chapter 3: Vector-Valued Functions,88
Chem 2e,o3,714,92.7,68.3,15,Chapter 15,41
Chem 2e,deepseek-chat,714,87.7,61.0,15,Chapter 15,41
Chem 2e,gemini-2.5-pro,714,91.2,65.9,15,Chapter 15,41
Chem 2e,o4-mini,714,90.3,73.2,15,Chapter 15,41
Chem 2e,gpt-5,714,92.3,68.3,15,Chapter 15,41
College Algebra,o3,2341,96.2,89.1,4,Chapter 4: Linear Functions,129
College Algebra,deepseek-chat,2341,90.6,79.8,4,Chapter 4: Linear Functions,129
College Algebra,gemini-2.5-pro,2341,95.0,88.4,4,Chapter 4: Linear Functions,129
College Algebra,o4-mini,2341,95.4,89.1,4,Chapter 4: Linear Functions,129
College Algebra,gpt-5,2341,95.6,90.7,4,Chapter 4: Linear Functions,129
College Physics 2e,o3,999,88.5,62.5,1,Chapter 1,16
College Physics 2e,deepseek-chat,999,76.1,20.0,9,Chapter 9,15
College Physics 2e,gemini-2.5-pro,999,87.2,61.1,5,Chapter 5,18
College Physics 2e,o4-mini,999,85.1,53.3,9,Chapter 9,15
College Physics 2e,gpt-5,999,88.1,73.3,9,Chapter 9,15
Elementary Algebra 2e,o3,4495,97.3,92.9,9,Chapter 9: Roots and Radical,622
Elementary Algebra 2e,deepseek-chat,4495,94.7,84.4,4,Chapter 4: Graphs,282
Elementary Algebra 2e,gemini-2.5-pro,4495,97.1,92.0,9,Chapter 9: Roots and Radical,622
Elementary Algebra 2e,o4-mini,4495,96.6,91.5,9,Chapter 9: Roots and Radical,622
Elementary Algebra 2e,gpt-5,4495,97.2,93.6,9,Chapter 9: Roots and Radical,622
Intellectual Property,o3,175,85.1,78.3,2,Chapter 2,23
Intellectual Property,deepseek-chat,175,84.6,81.1,4,Chapter 4,37
Intellectual Property,gemini-2.5-pro,175,90.3,82.6,2,Chapter 2,23
Intellectual Property,o4-mini,175,87.4,82.6,2,Chapter 2,23
Intellectual Property,gpt-5,175,86.9,78.3,2,Chapter 2,23
Intermediate Algebra 2e,o3,3262,96.8,91.9,4,Chapter 4: Systems of Linear Equations,236
Intermediate Algebra 2e,deepseek-chat,3262,93.9,81.6,3,Chapter 3: Graphs and Functions,201
Intermediate Algebra 2e,gemini-2.5-pro,3262,97.1,91.6,8,Chapter 8: Roots and Radical,431
Intermediate Algebra 2e,o4-mini,3262,95.9,87.3,4,Chapter 4: Systems of Linear Equations,236
Intermediate Algebra 2e,gpt-5,3262,96.9,89.0,4,Chapter 4: Systems of Linear Equations,236
Microbiology,o3,760,95.7,85.7,16,Chapter 16: Disease and Epidemiology,14
Microbiology,deepseek-chat,760,93.7,84.2,9,Chapter 9: Microbial Growth,38
Microbiology,gemini-2.5-pro,760,95.4,86.8,9,Chapter 9: Microbial Growth,38
Microbiology,o4-mini,760,95.5,88.5,20,Chapter 20: Laboratory Analysis of the Immune Response,26
Microbiology,gpt-5,760,95.5,88.5,15,Chapter 15: Microbial Mechanisms of Pathogenicity,26
Prealgebra 2e,o3,3729,98.3,94.0,11,Chapter 11: Graphs,100
Prealgebra 2e,deepseek-chat,3729,96.6,82.0,11,Chapter 11: Graphs,100
Prealgebra 2e,gemini-2.5-pro,3729,98.7,97.0,11,Chapter 11: Graphs,100
Prealgebra 2e,o4-mini,3729,98.3,95.8,5,Chapter 5: Decimals,478
Prealgebra 2e,gpt-5,3729,98.3,96.7,5,Chapter 5: Decimals,478
Precalc,o3,2594,95.6,87.4,12,Chapter 12: Introduction to Calculus,143
Precalc,deepseek-chat,2594,89.5,76.4,6,Chapter 6: Periodic Functions,89
Precalc,gemini-2.5-pro,2594,94.5,88.8,6,Chapter 6: Periodic Functions,89
Precalc,o4-mini,2594,94.6,84.6,12,Chapter 12: Introduction to Calculus,143
Precalc,gpt-5,2594,95.3,89.5,12,Chapter 12: Introduction to Calculus,143
Sociology,o3,185,94.6,77.8,12,Chapter 12,9
Sociology,deepseek-chat,185,90.3,70.0,16,Chapter 16,10
Sociology,gemini-2.5-pro,185,94.6,77.8,12,Chapter 12,9
Sociology,o4-mini,185,89.7,70.0,16,Chapter 16,10
Sociology,gpt-5,185,94.6,77.8,12,Chapter 12,9
Statistics High School,o3,583,90.1,80.0,12,Chapter 12: Linear Regression and Correlation,35
Statistics High School,deepseek-chat,583,81.3,60.5,2,Chapter 2: Descriptive Statistics,43
Statistics High School,gemini-2.5-pro,583,86.3,68.6,12,Chapter 12: Linear Regression and Correlation,35
Statistics High School,o4-mini,583,88.7,71.4,12,Chapter 12: Linear Regression and Correlation,35
Statistics High School,gpt-5,583,90.2,80.0,12,Chapter 12: Linear Regression and Correlation,35
Stats 2e,o3,508,90.6,76.7,12,Chapter 12,30
Stats 2e,deepseek-chat,508,82.3,50.0,2,Chapter 2,40
Stats 2e,gemini-2.5-pro,508,89.0,77.5,2,Chapter 2,40
Stats 2e,o4-mini,508,89.6,73.3,12,Chapter 12,30
Stats 2e,gpt-5,508,91.1,76.7,12,Chapter 12,30
US History,o3,218,92.7,66.7,18,Chapter 18,6
US History,deepseek-chat,218,90.4,66.7,16,Chapter 16,6
US History,gemini-2.5-pro,218,95.0,66.7,18,Chapter 18,6
US History,o4-mini,218,94.5,71.4,5,Chapter 5,7
US History,gpt-5,218,95.0,66.7,18,Chapter 18,6
University Physics V1,o3,909,91.5,84.2,12,Chapter 12: Sources of Magnetic Fields,38
University Physics V1,deepseek-chat,909,77.3,44.7,12,Chapter 12: Sources of Magnetic Fields,38
University Physics V1,gemini-2.5-pro,909,88.9,81.6,12,Chapter 12: Sources of Magnetic Fields,38
University Physics V1,o4-mini,909,90.6,81.6,12,Chapter 12: Sources of Magnetic Fields,38
University Physics V1,gpt-5,909,92.6,78.9,12,Chapter 12: Sources of Magnetic Fields,38
University Physics V2,o3,775,89.2,76.8,11,Chapter 11: Particle Physics and Cosmology,56
University Physics V2,deepseek-chat,775,72.5,47.8,13,Chapter 13: Electromagnetic Induction,46
University Physics V2,gemini-2.5-pro,775,86.5,71.4,11,Chapter 11: Particle Physics and Cosmology,56
University Physics V2,o4-mini,775,88.0,76.6,10,Chapter 10: Nuclear Physics,47
University Physics V2,gpt-5,775,89.0,75.0,11,Chapter 11: Particle Physics and Cosmology,56
University Physics V3,o3,585,88.0,81.6,7,Chapter 7: Quantum Mechanics,49
University Physics V3,deepseek-chat,585,78.1,67.8,2,Chapter 2: Geometric Optics and Image Formation,59
University Physics V3,gemini-2.5-pro,585,86.3,79.6,7,Chapter 7: Quantum Mechanics,49
University Physics V3,o4-mini,585,87.2,80.4,1,Chapter 1: The Nature of Light,46
University Physics V3,gpt-5,585,87.4,74.6,2,Chapter 2: Geometric Optics and Image Formation,59`;

function parseRows(): Row[] {
  return CSV_DATA.trim()
    .replace(/\r/g, "")
    .split("\n")
    .slice(1)
    .map((line) => {
      const [textbook, model, textbookQuestions, avg, minChapter] = line.split(",", 5);
      return {
        textbook,
        model,
        textbookQuestions: Number(textbookQuestions),
        avg: Number(avg),
        minChapter: Number(minChapter),
      };
    });
}

const rows = parseRows();
const textbookCount = new Set(rows.map((row) => row.textbook)).size;

function avg(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

const textbooks = [...new Set(rows.map((row) => row.textbook))].sort((a, b) => {
  const aValues = rows.filter((row) => row.textbook === a).map((row) => row.minChapter);
  const bValues = rows.filter((row) => row.textbook === b).map((row) => row.minChapter);
  return avg(aValues) - avg(bValues);
});

const groupedByTextbook = textbooks.map((textbook) => ({
  textbook,
  values: MODEL_ORDER.map((model) => rows.find((row) => row.textbook === textbook && row.model === model)!),
}));

const cdfSeries = MODEL_ORDER.map((model) => {
  const modelRows = rows.filter((row) => row.model === model);
  return {
    model,
    avgCounts: GRADE_BANDS.map((band) => modelRows.filter((row) => row.avg >= band.threshold).length),
    minCounts: GRADE_BANDS.map((band) => modelRows.filter((row) => row.minChapter >= band.threshold).length),
  };
});

function modelLabel(model: string) {
  return model;
}

function BarChart() {
  const left = 260;
  const right = 40;
  const top = 64;
  const bottom = 40;
  const chartWidth = 760;
  const groupHeight = 52;
  const barHeight = 8;
  const barGap = 2;
  const width = left + chartWidth + right;
  const height = top + bottom + groupedByTextbook.length * groupHeight;

  const xForValue = (value: number) => left + (value / 100) * chartWidth;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <text x={0} y={24} fontSize={24} fontWeight={700} fill="#111827">
        Minimum Chapter Accuracy by Textbook and Model
      </text>
      <text x={0} y={46} fontSize={12} fill="#4b5563">
        Textbooks are sorted by the average minimum chapter accuracy across models.
      </text>

      {[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map((tick) => {
        const x = xForValue(tick);
        return (
          <g key={tick}>
            <line x1={x} y1={top} x2={x} y2={height - bottom} stroke="#e5e7eb" strokeWidth={1} />
            <text x={x} y={height - 12} textAnchor="middle" fontSize={11} fill="#6b7280">
              {tick}
            </text>
          </g>
        );
      })}

      <line x1={left} y1={top} x2={left} y2={height - bottom} stroke="#111827" strokeWidth={1.5} />
      <line x1={left} y1={height - bottom} x2={left + chartWidth} y2={height - bottom} stroke="#111827" strokeWidth={1.5} />

      {groupedByTextbook.map((group, groupIndex) => {
        const groupTop = top + groupIndex * groupHeight;
        const labelY = groupTop + 22;
        return (
          <g key={group.textbook}>
            <text x={left - 12} y={labelY} textAnchor="end" fontSize={11} fill="#111827">
              {group.textbook}
            </text>
            {group.values.map((row, modelIndex) => {
              const y = groupTop + modelIndex * (barHeight + barGap);
              const widthPx = (row.minChapter / 100) * chartWidth;
              return (
                <g key={`${group.textbook}-${row.model}`}>
                  <rect
                    x={left}
                    y={y}
                    width={widthPx}
                    height={barHeight}
                    fill={MODEL_COLORS[row.model]}
                    rx={2}
                  >
                    <title>{`${group.textbook} | ${row.model} | ${row.minChapter.toFixed(1)}%`}</title>
                  </rect>
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}

function linePath(points: Array<{ x: number; y: number }>) {
  return points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
    .join(" ");
}

function CdfPanel({ model, avgCounts, minCounts }: { model: string; avgCounts: number[]; minCounts: number[] }) {
  const width = 350;
  const height = 220;
  const left = 40;
  const right = 16;
  const top = 28;
  const bottom = 46;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const xForIndex = (index: number) => left + (index / (GRADE_BANDS.length - 1)) * plotWidth;
  const yForCount = (count: number) => top + plotHeight - (count / textbookCount) * plotHeight;

  const avgPoints = avgCounts.map((count, index) => ({ x: xForIndex(index), y: yForCount(count) }));
  const minPoints = minCounts.map((count, index) => ({ x: xForIndex(index), y: yForCount(count) }));

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ background: "white" }}>
      <text x={left} y={16} fontSize={14} fontWeight={700} fill="#111827">
        {modelLabel(model)}
      </text>

      {[0, 5, 10, 15, 20, 25].map((tick) => {
        const y = yForCount(tick);
        return (
          <g key={tick}>
            <line x1={left} y1={y} x2={width - right} y2={y} stroke="#e5e7eb" strokeWidth={1} />
            <text x={left - 8} y={y + 4} textAnchor="end" fontSize={10} fill="#6b7280">
              {tick}
            </text>
          </g>
        );
      })}

      <line x1={left} y1={top} x2={left} y2={top + plotHeight} stroke="#111827" strokeWidth={1.5} />
      <line x1={left} y1={top + plotHeight} x2={width - right} y2={top + plotHeight} stroke="#111827" strokeWidth={1.5} />

      {GRADE_BANDS.map((band, index) => {
        const x = xForIndex(index);
        return (
          <text key={band.label} x={x} y={height - 18} textAnchor="middle" fontSize={10} fill="#6b7280">
            {band.label}
          </text>
        );
      })}

      <path
        d={linePath(avgPoints)}
        fill="none"
        stroke={MODEL_COLORS[model]}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d={linePath(minPoints)}
        fill="none"
        stroke={MODEL_COLORS[model]}
        strokeWidth={2.5}
        strokeDasharray="7 5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.8}
      />

      {avgPoints.map((point, index) => (
        <circle key={`avg-${index}`} cx={point.x} cy={point.y} r={2.8} fill={MODEL_COLORS[model]} />
      ))}
      {minPoints.map((point, index) => (
        <circle
          key={`min-${index}`}
          cx={point.x}
          cy={point.y}
          r={2.8}
          fill="white"
          stroke={MODEL_COLORS[model]}
          strokeWidth={1.5}
        />
      ))}
    </svg>
  );
}

export default function TextbookAccuracyPlotsCanvas() {
  return (
    <div
      style={{
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        background: "#f8fafc",
        color: "#111827",
        padding: 24,
        display: "flex",
        flexDirection: "column",
        gap: 28,
      }}
    >
      <div>
        <div style={{ fontSize: 30, fontWeight: 800, marginBottom: 8 }}>Textbook Accuracy Plots</div>
        <div style={{ fontSize: 14, color: "#475569", maxWidth: 980 }}>
          Built from `textbook_accuracy_summary.csv` for 26 textbooks and 5 models. The bar chart shows each
          model&apos;s minimum chapter accuracy for every textbook. The CDF panels show how many textbooks achieve
          each grade threshold or better, with solid lines for overall textbook average accuracy and dashed lines
          for minimum chapter accuracy.
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: 18,
          flexWrap: "wrap",
          alignItems: "center",
          fontSize: 13,
          color: "#334155",
        }}
      >
        {MODEL_ORDER.map((model) => (
          <div key={model} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 12, height: 12, borderRadius: 999, background: MODEL_COLORS[model] }} />
            <span>{modelLabel(model)}</span>
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: 16 }}>
          <div style={{ width: 22, height: 0, borderTop: "2.5px solid #111827" }} />
          <span>Avg textbook accuracy</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 22, height: 0, borderTop: "2.5px dashed #111827" }} />
          <span>Min chapter accuracy</span>
        </div>
      </div>

      <div style={{ background: "white", borderRadius: 16, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
        <BarChart />
      </div>

      <div style={{ background: "white", borderRadius: 16, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
        <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>Grade CDF by Model</div>
        <div style={{ fontSize: 13, color: "#475569", marginBottom: 16, maxWidth: 900 }}>
          X-axis grade buckets use the requested cutoffs: A+ is 97+, A is 93+, A- is 90+, B+ is 87+, B is 83+,
          B- is 80+, C+ is 77+, C is 73+, C- is 70+, D+ is 67+, D is 63+, D- is 60+, and F is below 60.
          Y-values are cumulative textbook counts at that grade or higher.
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 18 }}>
          {cdfSeries.map((series) => (
            <div
              key={series.model}
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 12,
                padding: 10,
                background: "#ffffff",
              }}
            >
              <CdfPanel model={series.model} avgCounts={series.avgCounts} minCounts={series.minCounts} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
