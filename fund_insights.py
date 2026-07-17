"""基金透视：持仓、行业与基金经理信息的确定性数据层。

本模块只展示公开披露的历史信息，不产生买入、卖出或收益预测结论。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 242


@dataclass(frozen=True)
class FundInsight:
    """供 UI 或命令行消费的基金透视结果。"""

    holdings: pd.DataFrame
    industries: pd.DataFrame
    holding_changes: pd.DataFrame
    managers: pd.DataFrame
    performance: dict[str, float | None]
    disclosures: dict[str, str | None]
    notices: list[str]


def _quarter_key(value: Any) -> tuple[int, int]:
    match = re.search(r"(\d{4})年\s*([1-4])季度", str(value))
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def _latest_quarter(frame: pd.DataFrame, period_column: str) -> pd.DataFrame:
    if frame.empty or period_column not in frame.columns:
        return frame.copy()
    keys = frame[period_column].map(_quarter_key)
    latest = max(keys, default=(0, 0))
    return frame.loc[keys == latest].copy()


def calculate_performance(nav_frame: pd.DataFrame) -> dict[str, float | None]:
    """根据单位净值计算基金历史与区间表现，所有结果均为百分比。"""
    required = {"净值日期", "单位净值"}
    if not required.issubset(nav_frame.columns):
        raise ValueError("净值数据缺少净值日期或单位净值列")

    frame = nav_frame.loc[:, ["净值日期", "单位净值"]].copy()
    frame["净值日期"] = pd.to_datetime(frame["净值日期"], errors="coerce")
    frame["单位净值"] = pd.to_numeric(frame["单位净值"], errors="coerce")
    frame = frame.dropna().sort_values("净值日期").drop_duplicates("净值日期")
    if len(frame) < 2:
        raise ValueError("真实净值数据样本不足")

    values = frame["单位净值"].to_numpy(dtype=float)
    start, end = values[0], values[-1]
    cumulative = (end / start - 1) * 100
    years = len(values) / TRADING_DAYS_PER_YEAR
    annualized = ((end / start) ** (1 / years) - 1) * 100 if years > 0 else None
    drawdown = values / np.maximum.accumulate(values) - 1

    def trailing_return(days: int) -> float | None:
        if len(values) <= days:
            return None
        return float((values[-1] / values[-days - 1] - 1) * 100)

    return {
        "成立以来收益": round(float(cumulative), 2),
        "年化收益": round(float(annualized), 2) if annualized is not None else None,
        "近一年收益": None if trailing_return(TRADING_DAYS_PER_YEAR) is None else round(trailing_return(TRADING_DAYS_PER_YEAR), 2),
        "近三年收益": None if trailing_return(TRADING_DAYS_PER_YEAR * 3) is None else round(trailing_return(TRADING_DAYS_PER_YEAR * 3), 2),
        "成立以来最大回撤": round(float(abs(drawdown.min()) * 100), 2),
    }


def build_holding_changes(current: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    """按证券代码比较两期前十大持仓；缺失证券按 0% 处理。"""
    columns = ["股票代码", "股票名称", "本期占净值比例", "上期占净值比例", "变化(百分点)"]
    if current.empty:
        return pd.DataFrame(columns=columns)

    def normalise(frame: pd.DataFrame, name: str) -> pd.DataFrame:
        if frame.empty or "股票代码" not in frame.columns:
            return pd.DataFrame(columns=["股票代码", name])
        result = frame.loc[:, ["股票代码", "占净值比例"]].copy()
        result["股票代码"] = result["股票代码"].astype(str).str.zfill(6)
        result[name] = pd.to_numeric(result["占净值比例"], errors="coerce").fillna(0.0)
        return result.loc[:, ["股票代码", name]]

    now = normalise(current, "本期占净值比例")
    old = normalise(previous, "上期占净值比例")
    names = current.loc[:, ["股票代码", "股票名称"]].copy() if "股票名称" in current.columns else pd.DataFrame({"股票代码": now["股票代码"], "股票名称": "-"})
    names["股票代码"] = names["股票代码"].astype(str).str.zfill(6)
    result = now.merge(old, on="股票代码", how="outer").merge(names, on="股票代码", how="left")
    result = result.fillna({"本期占净值比例": 0.0, "上期占净值比例": 0.0, "股票名称": "-"})
    result["变化(百分点)"] = result["本期占净值比例"] - result["上期占净值比例"]
    return result.loc[:, columns].sort_values("变化(百分点)", key=lambda item: item.abs(), ascending=False).reset_index(drop=True)


def _find_managers(manager_frame: pd.DataFrame, fund_code: str) -> pd.DataFrame:
    columns = ["姓名", "所属公司", "累计从业时间", "现任基金资产总规模", "现任基金最佳回报", "现任基金"]
    if manager_frame.empty or "现任基金代码" not in manager_frame.columns:
        return pd.DataFrame(columns=columns)

    code = str(fund_code).zfill(6)
    matches = manager_frame["现任基金代码"].fillna("").astype(str).map(
        lambda codes: code in re.findall(r"\d{6}", codes)
    )
    available = [column for column in columns if column in manager_frame.columns]
    return manager_frame.loc[matches, available].drop_duplicates().reset_index(drop=True)


def get_fund_insight(
    fund_code: str,
    ak_client: Any,
    year: int | None = None,
) -> FundInsight:
    """抓取公开基金数据并返回可审计的透视结果。

    ``ak_client`` 默认为调用方传入的 ``akshare`` 模块，便于测试替换数据源。
    """
    report_year = year or pd.Timestamp.today().year
    notices = [
        "持仓和行业信息来自基金定期报告，存在披露滞后，并非实时仓位。",
        "基金经理展示的是公开任职资料与基金历史表现；基金历史收益不等于经理个人可归因业绩。",
        "本功能仅用于风险理解与信息学习，不构成投资建议或买卖指令。",
    ]

    holding_frames: list[pd.DataFrame] = []
    for candidate_year in (report_year, report_year - 1):
        try:
            frame = ak_client.fund_portfolio_hold_em(symbol=fund_code, date=str(candidate_year))
            if not frame.empty:
                holding_frames.append(frame.copy())
        except Exception as error:  # 外部数据源不稳定时保留其他可用信息
            notices.append(f"{candidate_year} 年持仓数据暂不可用：{error}")

    all_holdings = pd.concat(holding_frames, ignore_index=True) if holding_frames else pd.DataFrame()
    period_column = "季度" if "季度" in all_holdings.columns else "截止时间"
    holdings = _latest_quarter(all_holdings, period_column)
    if not holdings.empty and "占净值比例" in holdings.columns:
        holdings["占净值比例"] = pd.to_numeric(holdings["占净值比例"], errors="coerce")
        holdings = holdings.sort_values("占净值比例", ascending=False).head(10).reset_index(drop=True)

    previous = pd.DataFrame()
    if not all_holdings.empty and period_column in all_holdings.columns:
        periods = sorted(set(all_holdings[period_column]), key=_quarter_key)
        if len(periods) > 1:
            previous = all_holdings.loc[all_holdings[period_column] == periods[-2]].copy()

    try:
        industry_frame = ak_client.fund_portfolio_industry_allocation_em(symbol=fund_code, date=str(report_year))
        industry_period = "截止时间" if "截止时间" in industry_frame.columns else "季度"
        industries = _latest_quarter(industry_frame, industry_period)
        if "占净值比例" in industries.columns:
            industries["占净值比例"] = pd.to_numeric(industries["占净值比例"], errors="coerce")
            industries = industries.sort_values("占净值比例", ascending=False).reset_index(drop=True)
    except Exception as error:
        industries = pd.DataFrame()
        notices.append(f"行业配置数据暂不可用：{error}")

    try:
        manager_frame = ak_client.fund_manager_em()
        managers = _find_managers(manager_frame, fund_code)
    except Exception as error:
        managers = pd.DataFrame()
        notices.append(f"基金经理公开资料暂不可用：{error}")

    nav_frame = ak_client.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
    performance = calculate_performance(nav_frame)
    disclosures = {
        "持仓披露期": None if holdings.empty or period_column not in holdings.columns else str(holdings.iloc[0][period_column]),
        "行业披露期": None if industries.empty else str(industries.iloc[0].get("截止时间", industries.iloc[0].get("季度", ""))),
    }
    return FundInsight(
        holdings=holdings,
        industries=industries,
        holding_changes=build_holding_changes(holdings, previous),
        managers=managers,
        performance=performance,
        disclosures=disclosures,
        notices=notices,
    )


def print_fund_insight(insight: FundInsight) -> None:
    """以命令行格式输出基金透视，供现有脚本直接调用。"""
    print("\n" + "=" * 70)
    print("基金透视（公开披露信息）")
    print("=" * 70)
    print(f"持仓披露期：{insight.disclosures['持仓披露期'] or '暂无'}")
    if insight.holdings.empty:
        print("前十大持仓：暂无可用数据")
    else:
        visible = [column for column in ["股票代码", "股票名称", "占净值比例", "持仓市值"] if column in insight.holdings.columns]
        print("\n前十大持仓：")
        print(insight.holdings.loc[:, visible].to_string(index=False))

    print(f"\n行业披露期：{insight.disclosures['行业披露期'] or '暂无'}")
    if not insight.industries.empty:
        visible = [column for column in ["行业类别", "占净值比例", "市值"] if column in insight.industries.columns]
        print(insight.industries.loc[:, visible].to_string(index=False))

    print("\n基金历史表现（非经理个人归因）：")
    for label, value in insight.performance.items():
        display = "数据不足" if value is None else f"{value:.2f}%"
        print(f"- {label}：{display}")

    print("\n基金经理公开资料：")
    print("暂无匹配经理资料" if insight.managers.empty else insight.managers.to_string(index=False))
    print("\n重要提示：")
    for notice in insight.notices:
        print(f"- {notice}")
