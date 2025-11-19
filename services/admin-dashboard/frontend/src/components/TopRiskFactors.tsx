/**
 * Top Risk Factors Component
 *
 * 상위 5개 위험 요인을 시각화합니다.
 * SHAP 기여도가 높은 feature들을 막대 그래프와 테이블로 표시합니다.
 */

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

export interface RiskFactor {
  factor: string;
  value: number;
  contribution: number;
  rank: number;
  impact: string; // "위험 증가" or "위험 감소"
}

interface TopRiskFactorsProps {
  riskFactors: RiskFactor[];
  title?: string;
  showChart?: boolean;
  showTable?: boolean;
}

/**
 * 커스텀 툴팁
 */
interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: RiskFactor & { absContribution: number };
  }>;
}

const CustomTooltip = ({ active, payload }: TooltipProps) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;

    return (
      <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
        <p className="font-semibold text-gray-900">{data.factor}</p>
        <p className="text-sm text-gray-600">
          Feature Value: <span className="font-medium">{data.value.toFixed(4)}</span>
        </p>
        <p
          className={`text-sm ${
            data.contribution > 0 ? "text-red-600" : "text-green-600"
          }`}
        >
          SHAP Contribution:{" "}
          <span className="font-medium">
            {data.contribution > 0 ? "+" : ""}
            {data.contribution.toFixed(4)}
          </span>
        </p>
        <p className="text-sm text-gray-500 italic">{data.impact}</p>
      </div>
    );
  }

  return null;
};

/**
 * T086: Top Risk Factors Visualization Component
 *
 * 상위 5개 위험 요인을 막대 그래프와 테이블로 시각화
 */
export const TopRiskFactors: React.FC<TopRiskFactorsProps> = ({
  riskFactors,
  title = "Top 5 Risk Factors",
  showChart = true,
  showTable = true,
}) => {
  // 절대값 기준 정렬 (이미 API에서 정렬되어 오지만 재확인)
  const sortedFactors = [...riskFactors].sort(
    (a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)
  );

  // 차트 데이터 준비
  const chartData = sortedFactors.map((factor) => ({
    ...factor,
    absContribution: Math.abs(factor.contribution),
  }));

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>

      {showChart && (
        <div className="mb-6">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="factor"
                angle={-45}
                textAnchor="end"
                height={80}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                label={{
                  value: "SHAP Contribution (Absolute)",
                  angle: -90,
                  position: "insideLeft",
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="absContribution" radius={[8, 8, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.contribution > 0 ? "#ef4444" : "#10b981"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {showTable && (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rank
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Factor
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Feature Value
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SHAP Contribution
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Impact
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedFactors.map((factor) => (
                <tr
                  key={factor.rank}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    #{factor.rank}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                    {factor.factor}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    {factor.value.toFixed(4)}
                  </td>
                  <td
                    className={`px-4 py-3 whitespace-nowrap text-sm font-semibold ${
                      factor.contribution > 0 ? "text-red-600" : "text-green-600"
                    }`}
                  >
                    {factor.contribution > 0 ? "+" : ""}
                    {factor.contribution.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        factor.contribution > 0
                          ? "bg-red-100 text-red-800"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {factor.impact}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sortedFactors.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No risk factors available</p>
        </div>
      )}

      <div className="mt-4 flex items-center gap-4 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <span>Increases Risk (Positive SHAP)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded"></div>
          <span>Decreases Risk (Negative SHAP)</span>
        </div>
      </div>
    </div>
  );
};

export default TopRiskFactors;
