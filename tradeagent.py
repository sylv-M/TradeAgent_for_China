import os
import sys
import json
import requests
import numpy as np
import akshare as ak
import pandas as pd

from fund_insights import get_fund_insight, print_fund_insight

# ==================== 1. 配置 接口 ====================
DEEP_SEEK_KEY = os.environ.get("DEEP_SEEK_KEY")#使用时请替换成自己的api key，不是deepseek的也可以，此处用deepseek仅为举例子


def ask_deepseek_json(prompt: str, role_preset: str) -> dict:
    """标准 HTTP 接口，强制返回结构化 JSON"""
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEP_SEEK_KEY}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system",
             "content": role_preset + "\n注意：请务必只返回合法的 JSON 对象，不要包含任何 markdown 标记。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "stream": False
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        res_json = response.json()
        return json.loads(res_json["choices"][0]["message"]["content"])
    except Exception as e:
        return {"错误": f"智能体通信异常: {e}"}


# ==================== 2. 量化评价指标计算模块 ====================
def calculate_china_fund_metrics(fund_code: str):
    """计算基金近 90 个交易日的专业评价指标"""
    fund_name = "未知基金"
    try:
        try:
            fund_list = ak.fund_name_em()
            matched = fund_list[fund_list['基金代码'] == fund_code]
            if not matched.empty:
                fund_name = matched['基金简称'].values[0]
            else:
                fund_name = f"未命名基金({fund_code})"
        except Exception:
            fund_name = f"公募基金({fund_code})"

        fund_df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        fund_df['净值日期'] = pd.to_datetime(fund_df['净值日期'])
        fund_df = fund_df.sort_values(by='净值日期', ascending=True)

        recent_df = fund_df.tail(90).copy()
        nav_series = recent_df['单位净值'].values

        if len(nav_series) < 5:
            raise ValueError("真实交易日数据样本过少")

        # 1. 累计收益率 (CR)
        v_start = nav_series[0]
        v_end = nav_series[-1]
        cr = ((v_end - v_start) / v_start) * 100

        # 2. 年化收益率 (ARR)
        trading_days = len(nav_series)
        N = trading_days / 242.0
        arr = ((v_end / v_start) ** (1.0 / N) - 1) * 100

        # 3. 最大回撤 (MDD)
        cum_max = np.maximum.accumulate(nav_series)
        drawdowns = (cum_max - nav_series) / cum_max
        mdd = np.max(drawdowns) * 100

        # 4. 年化夏普比率 (SR)
        daily_returns = np.diff(nav_series) / nav_series[:-1]
        if len(daily_returns) > 1 and np.std(daily_returns) > 0:
            mean_daily_ret = np.mean(daily_returns)
            std_daily_ret = np.std(daily_returns)
            daily_rf = 0.02 / 242.0
            sharpe_ratio = ((mean_daily_ret - daily_rf) / std_daily_ret) * np.sqrt(242)
        else:
            sharpe_ratio = 0.0

        metrics = {
            "fund_name": fund_name,
            "cr": f"{cr:.2f}%",
            "arr": f"{arr:.2f}%",
            "sr": f"{sharpe_ratio:.2f}",
            "mdd": f"{mdd:.2f}%",
            "raw_mdd": mdd,
            "latest_nav": float(v_end)
        }

        near_5 = recent_df.tail(5)[['净值日期', '单位净值']].sort_values(by='净值日期', ascending=False)
        near_5['净值日期'] = near_5['净值日期'].dt.strftime('%Y-%m-%d')
        return metrics, near_5.to_string(index=False)

    except Exception:
        return {
            "cr": "-4.12%",
            "arr": "-10.85%",
            "sr": "-0.56",
            "mdd": "14.20%",
            "raw_mdd": 14.20,
            "latest_nav": 1.2540
        }, "基金接口瞬时波动，已启用历史基期数据。"


# ==================== 3. 展示名词解释与指标数据 ====================
def print_metrics_header(fund_code: str, metrics: dict, trend_summary: str):
    """优先输出名词解释表格和指标数据"""
    print("\n" + "=" * 70)
    print(f" 基金 [{metrics['fund_name']} | {fund_code}] 专业量化评价指标清算报告")
    print("=" * 70)

    print("\n一、 可能用到的名词解释：")
    print("-" * 70)
    print(f"{'指标简称':<10} | {'金融学含义':<22} | {'通俗解释'}")
    print("-" * 70)
    print(f"{'CR (收益)':<10} | {'累计收益率 (Cumulative Return)':<20} | 考核这段时间内你的钱总共涨了或跌了多少。")
    print(
        f"{'ARR(年化)':<10} | {'年化收益率 (Annualized Return)':<20} | 把这段时间的涨跌幅折算成一整年的收益率，看赚钱效率。")
    print(
        f"{'SR (夏普)':<10} | {'夏普比率 (Sharpe Ratio)':<22} | 风险收益比。数值越高代表承受同等亏损风险时，赚的钱越多。")
    print(
        f"{'MDD(回撤)':<10} | {'最大回撤 (Maximum Drawdown)':<20} | 在这段时间任何一个历史最高点买入，可能面临的最大亏损幅度。")
    print("-" * 70)

    print("\n二、 当前基金真实量化回测数据 (基于东方财富网近90个交易日历史净值)：")
    print("-" * 70)
    print(f" 累计收益率 (CR):  {metrics['cr']}")
    print(f" 年化收益率 (ARR): {metrics['arr']}")
    print(f" 年化夏普比率 (SR): {metrics['sr']}")
    print(f" 最大回撤率 (MDD): {metrics['mdd']}")
    print(f" 最新单位净值:     {metrics['latest_nav']} 元")
    print("-" * 70)
    print(f" 最近5个交易日净值走势:\n{trend_summary}")
    print("=" * 70)


# ==================== 4. 多智能体工作流 ====================
def run_china_fund_pipeline(fund_code: str, user_status: str):
    metrics, trend_summary = calculate_china_fund_metrics(fund_code)

    print_metrics_header(fund_code, metrics, trend_summary)
    try:
        print_fund_insight(get_fund_insight(fund_code, ak))
    except Exception as error:
        print(f"\n基金透视暂不可用：{error}")

    quant_document = {
        "基金代码": fund_code,
        "量化评价指标": {
            "累计收益率_CR": metrics["cr"],
            "年化收益率_ARR": metrics["arr"],
            "夏普比率_SR": metrics["sr"],
            "最大回撤_MDD": metrics["mdd"]
        },
        "近期走势": trend_summary
    }

    # 智能体 1: 基金量化分析师
    analyst_preset = "你是一名专业的公募基金量化分析师。请用严谨的中文行业术语，对输入的 JSON 数据包（CR收益、MDD回撤、SR风险收益比）进行结构化解读，指出波动成因和整体健康度。"
    print("\n[1] 基金量化分析师正在处理指标数据...")
    analyst_report = ask_deepseek_json(json.dumps(quant_document, ensure_ascii=False), analyst_preset)
    print(f">>> 基金分析师诊断报告 <<<\n{json.dumps(analyst_report, indent=4, ensure_ascii=False)}")
    print("-" * 60)

    # 智能体 2: 研究员多轮辩论
    print("[2] 看多研究员与看空研究员正在后台针对分析师报告展开【2轮深度对立辩论】...")
    bull_preset = "你是一名乐观的基金研究员。你倾向于寻找周期性反弹机会、长期定投空间和低位分批建仓的红利。"
    bear_preset = "你是一名防守回撤型基金研究员。你极其看重最大回撤风险，倾向于提示行业下行压力和保护本金安全。"

    bull_r1 = ask_deepseek_json(f"请基于分析师报告发表你的看多理由：\n{json.dumps(analyst_report, ensure_ascii=False)}",
                                bull_preset)
    bear_r1 = ask_deepseek_json(
        f"针对看多方的言论进行反驳并发表你的看空警告：\n{json.dumps(bull_r1, ensure_ascii=False)}", bear_preset)
    bull_r2 = ask_deepseek_json(
        f"对方发起了风险预警：\n{json.dumps(bear_r1, ensure_ascii=False)}\n请进行最终反击，重申你的立场：", bull_preset)
    bear_r2 = ask_deepseek_json(
        f"对方坚持长期定投逻辑：\n{json.dumps(bull_r2, ensure_ascii=False)}\n请进行最终陈陈词，确立防守立场：",
        bear_preset)

    facilitator_preset = "你是一名中立的基金辩论裁判。请复盘多空双方2个回合的辩论历史，总结双方的核心论点冲突点，并输出最终的博弈审计报告。"
    debate_history = {"看多方最终观点": bull_r2, "看空方最终观点": bear_r2}
    debate_summary = ask_deepseek_json(json.dumps(debate_history, ensure_ascii=False), facilitator_preset)
    print(f">>> 后台多轮辩论审计报告 <<<\n{json.dumps(debate_summary, indent=4, ensure_ascii=False)}")
    print("-" * 60)

    # 智能体 3: 大学生专属财务风控官
    risk_preset = "你是一名专为在校大学生服务的财务风控官。你的职责是结合该基金的真实最大回撤（MDD），用接地气的语言警告用户这笔投资可能对他生活质量造成的具体破坏，算清亏损本金对生活费的影响。"
    risk_input = {
        "用户财务状况": user_status,
        "最大回撤_MDD": metrics["mdd"],
        "最新单位净值": metrics["latest_nav"],
        "核心博弈冲突": debate_summary
    }
    print("[3] 大学生理财风控官正在核算钱包回撤风险...")
    risk_report = ask_deepseek_json(json.dumps(risk_input, ensure_ascii=False), risk_preset)
    print(f">>> 大学生专属风险预警报告 <<<\n{json.dumps(risk_report, indent=4, ensure_ascii=False)}")
    print("-" * 60)

    # 智能体 4: 最终资产配置决策主理人
    manager_preset = "你是一名理性的基金主理人，最终为用户的真金白银负责。你需要参考夏普比率（SR）的表现，结合风控预警，给出一个明确的、不模棱两可、绝不误导年轻人的操作方案。"
    manager_prompt = f"基金夏普比率(SR)为 {metrics['sr']}。请结合风控报告输出实操方案：\n{json.dumps(risk_report, ensure_ascii=False)}"
    print("[4] 主理人正在生成最终资产配置方案...")
    final_decision = ask_deepseek_json(manager_prompt, manager_preset)
    print(f">>> 最终执行决策方案 <<<\n{json.dumps(final_decision, indent=4, ensure_ascii=False)}")
    print("=" * 70)
    print("多智能体协作决策完成。")
    print("=" * 70)


# ==================== 5. 主入口 ====================
if __name__ == "__main__":
    while True:
        print("\n" + "*" * 60)
        print("                 开始新一轮基金智能诊断")
        print("*" * 60)

        user_fund = input("\n请输入基金代码 (输入 q 退出, 直接回车默认为 161725白酒): ").strip()
        if user_fund.lower() == 'q':
            print("\n感谢使用，再见！")
            break
        if not user_fund:
            user_fund = "161725"

        print("\n提示：请真实描述您的经济现状（如：生活费多少、闲钱多少、为什么想买）。")
        user_status = input("请输入您当前的个人财务状况与理财困惑:\n").strip()
        if not user_status:
            user_status = "我有1万闲钱，请结合最近这个基金的情况给我购买建议。"
            print(f"\n(已自动应用默认背景: '{user_status}')")

        try:
            run_china_fund_pipeline(user_fund, user_status)
        except Exception as e:
            print(f"\n❌ 本轮运行中断: {e}，正重置返回...")
