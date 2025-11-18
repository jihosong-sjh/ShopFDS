"""
Feature Importance Analyzer

Random Forest 및 XGBoost 모델의 Feature Importance를 분석하여
사기 탐지에 가장 중요한 특징을 식별합니다.

주요 분석:
1. Random Forest: Gini Importance
2. XGBoost: Gain, Weight, Cover
3. Permutation Importance: 모델 독립적 중요도
4. SHAP 기반 글로벌 중요도 (선택사항)
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sklearn.inspection import permutation_importance
import matplotlib

matplotlib.use("Agg")  # 백엔드 설정 (GUI 없이 사용)
import matplotlib.pyplot as plt


logger = logging.getLogger(__name__)


class FeatureImportanceAnalyzer:
    """
    Feature Importance 분석 클래스

    여러 방법론을 통해 특징 중요도를 계산하고 시각화합니다.
    """

    def __init__(self):
        """초기화"""
        self.importances: Dict[str, pd.DataFrame] = {}

    def analyze_random_forest(
        self, model, feature_names: List[str], top_n: int = 20
    ) -> pd.DataFrame:
        """
        Random Forest Feature Importance 분석 (Gini Importance)

        Args:
            model: 학습된 RandomForestFraudModel
            feature_names: 특징 이름 목록
            top_n: 상위 N개 특징

        Returns:
            Feature importance DataFrame
        """
        logger.info("[FeatureImportance] Analyzing Random Forest importance")

        # Random Forest에서 importance 추출
        importances = model.get_feature_importances_full()

        # 상위 N개만 선택
        top_importances = importances.head(top_n)

        # 결과 저장
        self.importances["random_forest"] = top_importances

        logger.info(
            f"[FeatureImportance] Random Forest: Top feature is "
            f"'{top_importances.iloc[0]['feature']}' "
            f"(importance={top_importances.iloc[0]['importance']:.4f})"
        )

        return top_importances

    def analyze_xgboost(
        self, model, feature_names: List[str], top_n: int = 20
    ) -> pd.DataFrame:
        """
        XGBoost Feature Importance 분석 (Gain, Weight, Cover)

        Args:
            model: 학습된 XGBoostFraudModel
            feature_names: 특징 이름 목록
            top_n: 상위 N개 특징

        Returns:
            Feature importance DataFrame (Gain 기준)
        """
        logger.info("[FeatureImportance] Analyzing XGBoost importance")

        # XGBoost에서 importance 추출
        importances = model.get_feature_importances_full()

        # 상위 N개만 선택 (Gain 기준)
        top_importances = importances.head(top_n)

        # 결과 저장
        self.importances["xgboost"] = top_importances

        logger.info(
            f"[FeatureImportance] XGBoost: Top feature is "
            f"'{top_importances.iloc[0]['feature']}' "
            f"(gain={top_importances.iloc[0]['gain']:.4f})"
        )

        return top_importances

    def analyze_permutation_importance(
        self,
        model,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        top_n: int = 20,
        n_repeats: int = 10,
        random_state: int = 42,
    ) -> pd.DataFrame:
        """
        Permutation Importance 분석 (모델 독립적)

        특징을 무작위로 섞었을 때 성능 저하 정도를 측정하여 중요도 계산

        Args:
            model: 학습된 모델 (predict 메서드 필요)
            X_test: 테스트 특징 데이터
            y_test: 테스트 레이블
            top_n: 상위 N개 특징
            n_repeats: 반복 횟수
            random_state: 시드

        Returns:
            Permutation importance DataFrame
        """
        logger.info(
            f"[FeatureImportance] Analyzing Permutation Importance "
            f"(n_repeats={n_repeats})"
        )

        # Permutation Importance 계산
        result = permutation_importance(
            model,
            X_test,
            y_test,
            n_repeats=n_repeats,
            random_state=random_state,
            scoring="f1",
        )

        # DataFrame 생성
        importances_df = pd.DataFrame(
            {
                "feature": X_test.columns,
                "importance_mean": result.importances_mean,
                "importance_std": result.importances_std,
            }
        )

        # 중요도 높은 순으로 정렬
        importances_df = importances_df.sort_values(
            "importance_mean", ascending=False
        ).reset_index(drop=True)

        # 상위 N개만 선택
        top_importances = importances_df.head(top_n)

        # 결과 저장
        self.importances["permutation"] = top_importances

        logger.info(
            f"[FeatureImportance] Permutation: Top feature is "
            f"'{top_importances.iloc[0]['feature']}' "
            f"(mean={top_importances.iloc[0]['importance_mean']:.4f})"
        )

        return top_importances

    def compare_importances(self, methods: Optional[List[str]] = None) -> pd.DataFrame:
        """
        여러 방법론의 Feature Importance 비교

        Args:
            methods: 비교할 방법론 목록 (None이면 전체)

        Returns:
            비교 DataFrame
        """
        if not self.importances:
            raise ValueError(
                "No feature importances available. Run analyze_* methods first."
            )

        methods = methods or list(self.importances.keys())

        logger.info(f"[FeatureImportance] Comparing {len(methods)} methods")

        # 모든 특징 수집
        all_features = set()
        for method in methods:
            if method in self.importances:
                all_features.update(self.importances[method]["feature"].tolist())

        # 비교 DataFrame 생성
        comparison_data = []

        for feature in all_features:
            row = {"feature": feature}

            for method in methods:
                if method in self.importances:
                    df = self.importances[method]
                    feature_row = df[df["feature"] == feature]

                    if not feature_row.empty:
                        # Random Forest: importance
                        if method == "random_forest":
                            row[f"{method}_importance"] = feature_row.iloc[0][
                                "importance"
                            ]

                        # XGBoost: gain
                        elif method == "xgboost":
                            row[f"{method}_gain"] = feature_row.iloc[0]["gain"]

                        # Permutation: mean
                        elif method == "permutation":
                            row[f"{method}_mean"] = feature_row.iloc[0][
                                "importance_mean"
                            ]

                    else:
                        row[f"{method}_importance"] = 0.0

            comparison_data.append(row)

        comparison_df = pd.DataFrame(comparison_data)

        # 평균 중요도로 정렬
        numeric_cols = [col for col in comparison_df.columns if col != "feature"]
        if numeric_cols:
            comparison_df["avg_importance"] = comparison_df[numeric_cols].mean(axis=1)
            comparison_df = comparison_df.sort_values(
                "avg_importance", ascending=False
            ).reset_index(drop=True)

        return comparison_df

    def plot_importance(
        self,
        method: str,
        top_n: int = 20,
        figsize: Tuple[int, int] = (10, 8),
        save_path: Optional[str] = None,
    ) -> None:
        """
        Feature Importance 시각화 (수평 막대 그래프)

        Args:
            method: 방법론 (random_forest, xgboost, permutation)
            top_n: 상위 N개 특징
            figsize: 그림 크기
            save_path: 저장 경로 (옵션)
        """
        if method not in self.importances:
            raise ValueError(
                f"Method '{method}' not found. Run analyze_{method}() first."
            )

        logger.info(f"[FeatureImportance] Plotting {method} importance")

        df = self.importances[method].head(top_n)

        plt.figure(figsize=figsize)

        # 중요도 열 선택
        if method == "random_forest":
            importance_col = "importance"
            title = "Random Forest Feature Importance (Gini)"
        elif method == "xgboost":
            importance_col = "gain"
            title = "XGBoost Feature Importance (Gain)"
        elif method == "permutation":
            importance_col = "importance_mean"
            title = "Permutation Feature Importance"
        else:
            importance_col = "importance"
            title = "Feature Importance"

        # 수평 막대 그래프
        plt.barh(df["feature"], df[importance_col], color="steelblue")
        plt.xlabel("Importance")
        plt.ylabel("Feature")
        plt.title(title)
        plt.gca().invert_yaxis()  # 상위 특징이 위에 오도록
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            logger.info(f"[FeatureImportance] Plot saved to {save_path}")

        plt.close()

    def plot_comparison(
        self,
        top_n: int = 15,
        figsize: Tuple[int, int] = (12, 8),
        save_path: Optional[str] = None,
    ) -> None:
        """
        여러 방법론의 Feature Importance 비교 시각화

        Args:
            top_n: 상위 N개 특징
            figsize: 그림 크기
            save_path: 저장 경로 (옵션)
        """
        logger.info(f"[FeatureImportance] Plotting comparison for top {top_n} features")

        comparison_df = self.compare_importances()
        comparison_df = comparison_df.head(top_n)

        plt.figure(figsize=figsize)

        # 열 이름 매핑
        col_map = {}
        for col in comparison_df.columns:
            if "random_forest" in col:
                col_map[col] = "Random Forest"
            elif "xgboost" in col:
                col_map[col] = "XGBoost"
            elif "permutation" in col:
                col_map[col] = "Permutation"

        # 그룹화된 막대 그래프
        comparison_plot = comparison_df.rename(columns=col_map)
        numeric_cols = [
            col_map.get(col, col)
            for col in comparison_df.columns
            if col not in ["feature", "avg_importance"]
        ]

        if numeric_cols:
            comparison_plot.set_index("feature")[numeric_cols].plot(
                kind="barh", figsize=figsize
            )
            plt.xlabel("Importance")
            plt.ylabel("Feature")
            plt.title("Feature Importance Comparison (Multiple Methods)")
            plt.legend(title="Method", bbox_to_anchor=(1.05, 1), loc="upper left")
            plt.gca().invert_yaxis()
            plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            logger.info(f"[FeatureImportance] Comparison plot saved to {save_path}")

        plt.close()

    def get_top_features(self, method: str, top_n: int = 10) -> List[str]:
        """
        특정 방법론의 상위 N개 특징 이름 반환

        Args:
            method: 방법론
            top_n: 상위 N개

        Returns:
            특징 이름 목록
        """
        if method not in self.importances:
            raise ValueError(f"Method '{method}' not found.")

        return self.importances[method].head(top_n)["feature"].tolist()


def analyze_feature_importance(
    rf_model,
    xgb_model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_names: List[str],
    top_n: int = 20,
) -> Dict[str, pd.DataFrame]:
    """
    Feature Importance 종합 분석 (편의 함수)

    Args:
        rf_model: Random Forest 모델
        xgb_model: XGBoost 모델
        X_test: 테스트 데이터
        y_test: 테스트 레이블
        feature_names: 특징 이름 목록
        top_n: 상위 N개

    Returns:
        방법론별 importance DataFrame
    """
    analyzer = FeatureImportanceAnalyzer()

    # Random Forest
    rf_importance = analyzer.analyze_random_forest(rf_model, feature_names, top_n)

    # XGBoost
    xgb_importance = analyzer.analyze_xgboost(xgb_model, feature_names, top_n)

    # Permutation (XGBoost 기준)
    perm_importance = analyzer.analyze_permutation_importance(
        xgb_model, X_test, y_test, top_n
    )

    return {
        "random_forest": rf_importance,
        "xgboost": xgb_importance,
        "permutation": perm_importance,
        "comparison": analyzer.compare_importances(),
    }
