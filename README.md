# China-Fund-Multi-Agent
> *如需中文版本，请点击:* (README_CN.md)

An interactive, multi-agent quantitative framework designed for financial diagnostics and risk mitigation of Chinese mutual funds, tailored specifically for undergraduate retail investors.

## Academic Attribution & Inspiration
This framework is heavily inspired by and adapted from the pioneering research conducted by scholars from **UCLA** and **MIT**:
* **Paper:** *TradingAgents: Multi-Agents LLM Financial Trading Framework* (2024/2025)
* **Authors:** Yijia Xiao (UCLA), Edward Sun (UCLA), Di Luo (MIT), and Wei Wang (UCLA)

## Original Framework & Repository
This project is built upon the theoretical architecture and open-source implementation of the original paper:
* **Official Repository:** [TauricResearch/TradingAgents](https://github.org/TauricResearch/TradingAgents)
* **Paper Link:** [arXiv:2412.20138](https://arxiv.org/abs/2412.20138)

Please star the original repository if you find their foundational multi-agent trading framework inspiring!

## Key Features & Fund Transparency Analysis

Prior to executing quantitative NAV diagnostics, the framework performs a comprehensive Fund Transparency Analysis based on publicly disclosed filings:

* **Top Holdings & Sector Allocation:** Detailed breakdown of top 10 holdings and sector exposures from the latest disclosure period.
* **Portfolio Adjustments:** Quarter-over-quarter position changes compared to previous reporting periods.
* **Fund Manager Profiles:** Public tenure records, total Assets Under Management (AUM), and career-best returns across active funds.
* **Historical Performance Metrics:** Complete track record including return since inception, 1-year/3-year returns, annualized return, and maximum drawdown since inception.

> **Note on Data Disclosure & Limitations:** Holdings and sector data are extracted from periodic regulatory filings and represent historical disclosures rather than real-time positions. Furthermore, overall fund performance may not directly correlate with an individual manager's isolated attribution. This feature is strictly designed for risk exposure assessment and information management—**it does not generate trading signals, buy/sell orders, or return forecasts.**

## Key Adaptations for Chinese Undergraduates
While the original *TradingAgents* framework focused on LLM-driven rule-based trading of US equities (e.g., AAPL, NVDA) via global APIs, this repository adapts the workflow to fit the specific needs and financial boundaries of Chinese college students:

1. **Domestic Mutual Fund Anchoring:** Replaced US stock tools with native Chinese mutual fund infrastructure (`akshare`), allowing analysis of popular domestic sector funds (e.g., Consumer/Liquor, Semiconductors, Healthcare).
2. **Rigorous MIT Evaluation Metrics:** Fully replicated the core portfolio evaluation criteria specified in the original paper's appendix (Equations S1-S4), computing real-time quantitative metrics based on the last 90 trading days:
   * **CR** (Cumulative Return)
   * **ARR** (Annualized Return)
   * **SR** (Sharpe Ratio)
   * **MDD** (Maximum Drawdown)
3. **Structured Communication Protocol:** Enforced the paper's rigid JSON-object messaging constraints between agents to neutralize LLM hallucinations and eliminate the text-overload "telephone effect" common in standard natural language pipelines.
4. **Student-Centric Risk Guardrails:** Configured the multi-agent debate and Risk Management nodes to translate raw quantitative volatility (specifically MDD) into relatable, empathetic daily-allowance financial warnings (e.g., factoring in a typical 2,000 RMB/month student budget) to prevent impulse investing or capital erosion.

## Local Verification

To run tests locally and verify the environment setup:

```bash
python -m unittest discover -s tests -v
