import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell
} from "recharts";

const palette = ["#0f766e", "#2f855a", "#84cc16", "#16a34a", "#65a30d", "#22c55e", "#4d7c0f", "#4ade80"];

function ChartCard({ title, children }) {
  return (
    <section className="card chart-card">
      <div className="card-head">
        <h3>{title}</h3>
      </div>
      {children}
    </section>
  );
}

function ActivityCharts({ chartData }) {
  const monthly = chartData?.monthly_predictions || [];
  const crops = chartData?.crop_distribution || [];
  const survey = chartData?.survey_trend || [];

  return (
    <div className="chart-grid">
      <ChartCard title="Monthly Yield Trend (q/acre)">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={monthly}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip formatter={(value) => [`${value} q/acre`, "Avg Yield"]} />
            <Legend />
            <Line type="monotone" dataKey="avg_yield_quintal_acre" stroke="#166534" strokeWidth={3} name="Avg Yield" />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Crop Activity Distribution">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie data={crops} dataKey="count" nameKey="crop" outerRadius={100} label>
              {crops.map((entry, index) => (
                <Cell key={entry.crop} fill={palette[index % palette.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Survey Satisfaction Trend">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={survey}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis domain={[0, 5]} />
            <Tooltip />
            <Bar dataKey="avg_satisfaction" fill="#65a30d" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

export default ActivityCharts;
