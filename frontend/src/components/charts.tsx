import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Series } from "@/services/endpoints";

const PALETTE = ["#2563eb", "#0ea5e9", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#ec4899", "#64748b"];
const SEVERITY_COLOR: Record<string, string> = {
  info: "#64748b",
  low: "#0ea5e9",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
  processed: "#10b981",
  invalid: "#ef4444",
  duplicate: "#f59e0b",
  quarantined: "#f97316",
  protected: "#10b981",
  "not protected": "#64748b",
};

const axis = { stroke: "#64748b", fontSize: 11 };
const tooltipStyle = {
  contentStyle: { background: "#121826", border: "1px solid #1f2937", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "#e5e7eb" },
};

export function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</h3>
      <div className="h-52">{children}</div>
    </div>
  );
}

export function BarSeries({ data, colorByLabel }: { data: Series[]; colorByLabel?: boolean }) {
  if (!data.length) return <Empty />;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -18 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis dataKey="label" {...axis} interval={0} angle={-20} textAnchor="end" height={50} />
        <YAxis allowDecimals={false} {...axis} />
        <Tooltip {...tooltipStyle} cursor={{ fill: "#ffffff08" }} />
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => (
            <Cell
              key={d.label}
              fill={colorByLabel ? SEVERITY_COLOR[d.label] ?? PALETTE[i % PALETTE.length] : PALETTE[i % PALETTE.length]}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DonutSeries({ data }: { data: Series[] }) {
  const filtered = data.filter((d) => d.value > 0);
  if (!filtered.length) return <Empty />;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie data={filtered} dataKey="value" nameKey="label" innerRadius={40} outerRadius={70} paddingAngle={2}>
          {filtered.map((d, i) => (
            <Cell key={d.label} fill={SEVERITY_COLOR[d.label] ?? PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip {...tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function TimeSeries({ data }: { data: { bucket: string; count: number }[] }) {
  if (!data.length) return <Empty />;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 4, right: 12, bottom: 4, left: -18 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis dataKey="bucket" {...axis} tickFormatter={(v) => String(v).slice(5, 16)} />
        <YAxis allowDecimals={false} {...axis} />
        <Tooltip {...tooltipStyle} />
        <Line type="monotone" dataKey="count" stroke="#2563eb" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function Empty() {
  return (
    <div className="flex h-full items-center justify-center text-xs text-gray-600">no data yet</div>
  );
}
