# China-Fund-Multi-Agent

An interactive, multi-agent quantitative framework designed for financial diagnostics and risk mitigation of Chinese mutual funds, tailored specifically for undergraduate retail investors.

## 基金透视（新增）

在原有净值诊断前，程序会新增一段基于公开披露资料的基金透视：

- 最新披露期的前十大持仓和行业配置；
- 与上一个报告期相比的持仓比例变化；
- 基金经理的公开任职资料、在管规模和现任基金最佳回报；
- 基金成立以来、近一年、近三年、年化收益和成立以来最大回撤。

持仓/行业数据来自定期报告，存在披露滞后，并非实时仓位；“基金历史表现”也不等于基金经理的个人可归因业绩。该功能只用于理解风险暴露和管理信息，**不产生买卖指令或收益预测**。

### 本地验证

```bash
python -m unittest discover -s tests -v
```

## Academic Attribution & Inspiration
This framework is heavily inspired by and adapted from the pioneering research conducted by scholars from **UCLA** and **MIT**:
* **Paper:** *TradingAgents: Multi-Agents LLM Financial Trading Framework* (2024/2025)
* **Authors:** Yijia Xiao (UCLA), Edward Sun (UCLA), Di Luo (MIT), and Wei Wang (UCLA)

##  Original Framework & Repository
This project is built upon the theoretical architecture and open-source implementation of the original paper:
* **Official Repository:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)
* **Paper Link:** [arXiv:2412.20138](https://arxiv.org/abs/2412.20138)

Please star the original repository if you find their foundational multi-agent trading framework inspiring!

##  Key Adaptations for Chinese Undergraduates
While the original *TradingAgents* framework focused on LLM-driven rule-based trading of US equities (e.g., AAPL, NVDA) via global APIs, this repository adapts the workflow to fit the specific needs and financial boundaries of Chinese college students:

1. **Domestic Mutual Fund Anchoring:** Replaced US stock tools with native Chinese mutual fund infrastructure (`akshare`), allowing analysis of popular domestic sector funds (e.g., Consumer/Liquor, Semiconductors, Healthcare).
2. **Rigorous MIT Evaluation Metrics:** Fully replicated the core portfolio evaluation criteria specified in the original paper's appendix (Equations S1-S4), computing real-time quantitative metrics based on the last 90 trading days:
   * **CR** (Cumulative Return)
   * **ARR** (Annualized Return)
   * **SR** (Sharpe Ratio)
   * **MDD** (Maximum Drawdown)
3. **Structured Communication Protocol:** Enforced the paper's rigid JSON-object messaging constraints between agents to neutralize LLM hallucinations and eliminate the text-overload "telephone effect" common in standard natural language pipelines.
4. **Student-Centric Risk Guardrails:** Configured the multi-agent debate and Risk Management nodes to translate raw quantitative volatility (specifically MDD) into relatable, empathetic daily-allowance financial warnings (e.g., factoring in a typical 2,000 RMB/month student budget) to prevent impulse investing or capital erosion.
