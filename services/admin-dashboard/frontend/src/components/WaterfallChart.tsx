/**
 * Waterfall Chart Component
 *
 * SHAP 값을 워터폴 차트로 시각화합니다.
 * Feature별 기여도를 누적 막대 그래프로 표현하여
 * base_value에서 최종 예측값까지의 변화를 보여줍니다.
 */

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

export interface SHAPValue {
  feature: string;
  value: number;
  shap_value: number;
  contribution: number;
  rank: number;
}

interface WaterfallChartProps {
  shapValues: SHAPValue[];
  title?: string;
  height?: number;
}

/**
 * 워터폴 차트 데이터 변환
 *
 * SHAP 값을 누적 막대 그래프용 데이터로 변환
 */
const transformToWaterfallData = (shapValues: SHAPValue[]) => {
  const sortedValues = [...shapValues].sort((a, b) => a.rank - b.rank);

  let cumulative = 0;
  const data = sortedValues.map((item) => {
    const start = cumulative;
    cumulative += item.contribution;

    return {
      name: item.feature === "base_value" ? "Base Value" : item.feature,
      contribution: item.contribution,
      start: start,
      end: cumulative,
      value: item.value,
      isBase: item.feature === "base_value",
      isPositive: item.contribution > 0,
    };
  });

  // 최종 예측값 추가
  data.push({
    name: "Final Prediction",
    contribution: 0,
    start: cumulative,
    end: cumulative,
    value: cumulative,
    isBase: false,
    isPositive: cumulative > 0,
  });

  return data;
};

/**
 * 커스텀 툴팁
 */
interface WaterfallDataPoint {
  name: string;
  contribution: number;
  start: number;
  end: number;
  value: number;
  isBase: boolean;
  isPositive: boolean;
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: WaterfallDataPoint;
  }>;
}

const CustomTooltip = ({ active, payload }: TooltipProps) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;

    return (
      <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
        <p className="font-semibold text-gray-900">{data.name}</p>
        {!data.isBase && data.name !== "Final Prediction" && (
          <>
            <p className="text-sm text-gray-600">
              Feature Value: <span className="font-medium">{data.value.toFixed(4)}</span>
            </p>
            <p
              className={`text-sm ${
                data.isPositive ? "text-red-600" : "text-green-600"
              }`}
            >
              Contribution:{" "}
              <span className="font-medium">
                {data.contribution > 0 ? "+" : ""}
                {data.contribution.toFixed(4)}
              </span>
            </p>
          </>
        )}
        <p className="text-sm text-gray-600">
          Cumulative: <span className="font-medium">{data.end.toFixed(4)}</span>
        </p>
      </div>
    );
  }

  return null;
};

/**
 * T085: Waterfall Chart Component
 *
 * SHAP 값 기여도를 워터폴 차트로 시각화
 */
export const WaterfallChart: React.FC<WaterfallChartProps> = ({
  shapValues,
  title = "SHAP Waterfall Chart - Feature Contributions",
  height = 400,
}) => {
  const data = transformToWaterfallData(shapValues);

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>

      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 100 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            angle={-45}
            textAnchor="end"
            height={100}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            label={{
              value: "Prediction Score",
              angle: -90,
              position: "insideLeft",
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" />

          {/* Stacked bars for waterfall effect */}
          <Bar dataKey="start" stackId="a" fill="transparent" />
          <Bar dataKey="contribution" stackId="a">
            {data.map((entry, index) => {
              let fill = "#93c5fd"; // base value color (light blue)

              if (entry.name === "Final Prediction") {
                fill = entry.isPositive ? "#ef4444" : "#10b981"; // red or green
              } else if (!entry.isBase) {
                fill = entry.isPositive ? "#fca5a5" : "#86efac"; // light red or light green
              }

              return <Cell key={`cell-${index}`} fill={fill} />;
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 flex flex-wrap gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-300 rounded"></div>
          <span>Base Value</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-300 rounded"></div>
          <span>Increases Risk</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-300 rounded"></div>
          <span>Decreases Risk</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <span>Final Prediction (High Risk)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded"></div>
          <span>Final Prediction (Low Risk)</span>
        </div>
      </div>
    </div>
  );
};

export default WaterfallChart;
