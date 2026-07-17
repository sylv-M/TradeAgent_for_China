import unittest

import pandas as pd

from fund_insights import build_holding_changes, calculate_performance, get_fund_insight


class FakeAkshare:
    def fund_portfolio_hold_em(self, symbol, date):
        if date == "2026":
            return pd.DataFrame(
                {
                    "股票代码": ["000001", "600000", "300001"],
                    "股票名称": ["平安银行", "浦发银行", "特锐德"],
                    "占净值比例": [8.0, 5.0, 3.0],
                    "季度": ["2026年1季度股票投资明细"] * 3,
                }
            )
        return pd.DataFrame(
            {
                "股票代码": ["000001", "600000"],
                "股票名称": ["平安银行", "浦发银行"],
                "占净值比例": [4.0, 7.0],
                "季度": ["2025年4季度股票投资明细"] * 2,
            }
        )

    def fund_portfolio_industry_allocation_em(self, symbol, date):
        return pd.DataFrame(
            {"行业类别": ["金融业", "信息技术"], "占净值比例": [18.0, 9.0], "截止时间": ["2026-03-31", "2026-03-31"]}
        )

    def fund_manager_em(self):
        return pd.DataFrame(
            {
                "姓名": ["张三", "李四"],
                "所属公司": ["示例基金", "另一基金"],
                "现任基金代码": ["000001,000002", "000003"],
                "现任基金": ["示例基金A", "示例基金B"],
                "累计从业时间": [1000, 600],
                "现任基金资产总规模": [10.5, 8.2],
                "现任基金最佳回报": [15.2, 9.1],
            }
        )

    def fund_open_fund_info_em(self, symbol, indicator):
        return pd.DataFrame(
            {"净值日期": pd.date_range("2025-01-01", periods=300, freq="B"), "单位净值": [1 + i * 0.001 for i in range(300)]}
        )


class FundInsightTests(unittest.TestCase):
    def test_calculate_performance_uses_nav_values(self):
        frame = pd.DataFrame({"净值日期": ["2025-01-01", "2025-01-02", "2025-01-03"], "单位净值": [1.0, 1.2, 1.1]})
        result = calculate_performance(frame)
        self.assertEqual(result["成立以来收益"], 10.0)
        self.assertEqual(result["成立以来最大回撤"], 8.33)

    def test_holding_changes_preserve_new_and_removed_positions(self):
        current = pd.DataFrame({"股票代码": ["1", "2"], "股票名称": ["甲", "乙"], "占净值比例": [5.0, 2.0]})
        previous = pd.DataFrame({"股票代码": ["1", "3"], "股票名称": ["甲", "丙"], "占净值比例": [1.0, 4.0]})
        changes = build_holding_changes(current, previous)
        self.assertSetEqual(set(changes["股票代码"]), {"000001", "000002", "000003"})
        self.assertEqual(changes.loc[changes["股票代码"] == "000001", "变化(百分点)"].iloc[0], 4.0)

    def test_fund_insight_filters_manager_by_exact_fund_code(self):
        insight = get_fund_insight("000001", FakeAkshare(), year=2026)
        self.assertEqual(insight.disclosures["持仓披露期"], "2026年1季度股票投资明细")
        self.assertEqual(insight.managers["姓名"].tolist(), ["张三"])
        self.assertEqual(insight.holding_changes.loc[0, "股票代码"], "000001")


if __name__ == "__main__":
    unittest.main()
