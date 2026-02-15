export const mockStats = {
  totalCapital: 200.0,
  todayPnL: 5.5,
  todayPnLPercent: 2.75,
  winRate: 65.5,
  totalTrades: 50,
  winningTrades: 33,
  systemStatus: "running" as const,
  uptime: "2h 30m",
  mode: "paper" as const,
};

export const mockPnLHistory = [
  { date: "02/09", pnl: 0 },
  { date: "02/10", pnl: 2.3 },
  { date: "02/11", pnl: -1.2 },
  { date: "02/12", pnl: 3.8 },
  { date: "02/13", pnl: 1.5 },
  { date: "02/14", pnl: -0.8 },
  { date: "02/15", pnl: 5.5 },
];

export const mockPositions = [
  { id: "1", market: "特朗普胜选 2024", outcome: "YES" as const, shares: 50, avgPrice: 0.65, currentPrice: 0.7, pnl: 2.5, pnlPercent: 7.69 },
  { id: "2", market: "比特币年底 > $100k", outcome: "NO" as const, shares: 30, avgPrice: 0.55, currentPrice: 0.5, pnl: 1.5, pnlPercent: 9.09 },
  { id: "3", market: "美联储3月降息", outcome: "YES" as const, shares: 20, avgPrice: 0.4, currentPrice: 0.35, pnl: -1.0, pnlPercent: -12.5 },
  { id: "4", market: "以太坊 ETF 获批", outcome: "YES" as const, shares: 40, avgPrice: 0.72, currentPrice: 0.78, pnl: 2.4, pnlPercent: 8.33 },
];

const markets = ["特朗普胜选 2024", "比特币年底 > $100k", "美联储3月降息", "以太坊 ETF 获批", "GPT-5 年内发布", "SpaceX 火星任务", "苹果市值 > $4T", "黄金 > $2500"];
const types = ["BUY_YES", "BUY_NO", "SELL_YES", "SELL_NO"] as const;
const modes = ["paper", "live"] as const;

function generateTrades(count: number) {
  const trades = [];
  const baseDate = new Date(2026, 1, 15, 10, 30, 0);
  for (let i = 0; i < count; i++) {
    const d = new Date(baseDate.getTime() - i * 3600000 * (1 + Math.random() * 2));
    const price = +(0.3 + Math.random() * 0.5).toFixed(2);
    const amount = +(5 + Math.random() * 20).toFixed(2);
    trades.push({
      id: String(i + 1),
      timestamp: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`,
      market: markets[i % markets.length],
      type: types[i % types.length],
      mode: modes[i % 5 === 0 ? 1 : 0],
      amount,
      price,
      shares: +(amount / price).toFixed(2),
      status: "filled" as const,
    });
  }
  return trades;
}

export const mockTrades = generateTrades(47);

export const mockPredictions = [
  { id: "1", timestamp: "2026-02-15 09:00:00", market: "特朗普胜选 2024", llmProbability: 0.75, marketPrice: 0.65, confidence: "high" as const, reasoning: "基于历史民调数据和摇摆州分析，当前市场低估了胜选概率。", result: null, status: "pending" as const },
  { id: "2", timestamp: "2026-02-15 08:30:00", market: "比特币年底 > $100k", llmProbability: 0.35, marketPrice: 0.45, confidence: "medium" as const, reasoning: "宏观经济不确定性较大，当前市场高估了突破概率。", result: null, status: "pending" as const },
  { id: "3", timestamp: "2026-02-14 09:00:00", market: "美联储3月降息", llmProbability: 0.6, marketPrice: 0.4, confidence: "high" as const, reasoning: "通胀数据持续回落，就业市场降温，降息概率被低估。", result: true, status: "correct" as const },
  { id: "4", timestamp: "2026-02-13 09:00:00", market: "以太坊 ETF 获批", llmProbability: 0.8, marketPrice: 0.72, confidence: "high" as const, reasoning: "SEC 态度转变明显，多家机构已提交申请。", result: true, status: "correct" as const },
  { id: "5", timestamp: "2026-02-12 09:00:00", market: "GPT-5 年内发布", llmProbability: 0.55, marketPrice: 0.6, confidence: "low" as const, reasoning: "OpenAI 开发进度不明确，竞争对手施压可能加速发布。", result: false, status: "incorrect" as const },
];

export const mockRecentActivity = [
  { id: "1", time: "10:30", type: "trade" as const, description: "买入 特朗普胜选 YES @ $0.65", amount: 10.0 },
  { id: "2", time: "09:15", type: "trade" as const, description: "买入 比特币 > $100k NO @ $0.55", amount: 8.0 },
  { id: "3", time: "09:00", type: "prediction" as const, description: "预测 特朗普胜选 75% YES (市场 65%)", amount: null },
  { id: "4", time: "08:30", type: "prediction" as const, description: "预测 比特币 > $100k 35% YES (市场 45%)", amount: null },
  { id: "5", time: "08:00", type: "system" as const, description: "系统启动，开始扫描市场", amount: null },
];

export const mockSettings = {
  risk: { initialCapital: 200, maxPositionSize: 20, confidenceThreshold: 75, dailyLossLimit: 30 },
  api: { llmKey: "sk-xxxx****xxxx", model: "glm-4", proxyWallet: "0x1234...5678" },
  market: { minLiquidity: 10000, minDaysToExpiry: 7 },
};
