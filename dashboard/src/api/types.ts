/**
 * Shared TypeScript type definitions for API responses.
 *
 * These types match the backend Pydantic models for type-safe API calls.
 *
 * Story 7.6: 前端 API 集成
 */

// ============================================================================
// Statistics Types
// ============================================================================

export interface OverviewStats {
  initial_capital: number;
  wallet_balance: number | null;
  position_value: number;
  position_pnl: number;
  current_capital: number;
  total_pnl: number;
  total_pnl_pct: number;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  open_positions: number;
  trading_enabled: boolean;
  mode: string;
  wallet_balance_error: string | null;
}

export interface DailyStatsItem {
  date: string;
  starting_capital: number;
  ending_capital: number | null;
  total_pnl: number | null;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number | null;
}

export interface CapitalHistoryPoint {
  date: string;
  capital: number;
}

export interface WinRateHistoryPoint {
  date: string;
  win_rate: number;
}

export interface TradesByDayPoint {
  date: string;
  count: number;
}

export interface PerformanceData {
  capital_history: CapitalHistoryPoint[];
  win_rate_history: WinRateHistoryPoint[];
  trades_by_day: TradesByDayPoint[];
}

// ============================================================================
// System Status Types
// ============================================================================

export interface SystemStatus {
  trading_enabled: boolean;
  mode: string;
  current_capital: number;
  daily_pnl: number;
  open_positions: number;
  consecutive_losses: number;
  reduced_mode: boolean;
  last_market_fetch: string | null;
  uptime_hours: number | null;
  wallet_balance: number | null;
  wallet_balance_error: string | null;
}

export interface SanitizedSettings {
  trading_mode: string;
  initial_capital: number;
  trade_unit: number;
  max_single_ratio: number;
  min_confidence: number;
  min_edge: number;
  daily_loss_limit: number;
  max_open_markets: number;
  llm_model: string;
  llm_api_base: string;
  llm_api_key: string;
  polymarket_pk: string;
  proxy_wallet: string;
}

// ============================================================================
// Market Types
// ============================================================================

export type MarketCategory = 'politics' | 'business' | 'technology' | 'economics' | 'crypto' | 'sports' | 'entertainment' | 'other';

export interface MarketListItem {
  id: string;
  title: string;
  category: MarketCategory | null;
  yes_price: number | null;
  no_price: number | null;
  liquidity: number | null;
  deadline: string | null;
  resolution_status: string | null;
}

export interface MarketResponse {
  id: string;
  title: string;
  description: string | null;
  category: MarketCategory | null;
  yes_price: number | null;
  no_price: number | null;
  liquidity: number | null;
  deadline: string | null;
  resolution_status: string | null;
  resolution_outcome: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MarketListQueryParams {
  page?: number;
  per_page?: number;
  status?: 'active' | 'resolved' | 'all';
  category?: MarketCategory;
}

// ============================================================================
// Position Types
// ============================================================================

export type PositionOutcome = 'YES' | 'NO';
export type PositionStatus = 'open' | 'closed';
export type CacheFreshness = 'FRESH' | 'STALE' | 'EXPIRED';

export interface PositionListItem {
  id: number;
  market_id: string;
  outcome: PositionOutcome;
  shares: number;
  avg_price: number;
  cur_price: number | null;
  current_value: number | null;
  pnl: number | null;
  status: PositionStatus;
  opened_at: string | null;
}

export interface PositionListResponse {
  positions: PositionListItem[];
  cache_freshness: CacheFreshness;
  cache_age_seconds: number;
  total_count: number;
}

export interface PositionResponse {
  id: number;
  market_id: string;
  outcome: PositionOutcome;
  shares: number;
  avg_price: number;
  initial_value: number | null;
  current_value: number | null;
  pnl: number | null;
  status: PositionStatus;
  opened_at: string | null;
  closed_at: string | null;
}

// ============================================================================
// Trade Types
// ============================================================================

export type TradeType = 'BUY_YES' | 'BUY_NO' | 'SELL_YES' | 'SELL_NO';
export type TradeMode = 'PAPER' | 'LIVE';
export type TradeStatus = 'PENDING' | 'FILLED' | 'FAILED' | 'CANCELLED';

export interface TradeListItem {
  id: number;
  market_id: string;
  trade_type: TradeType;
  mode: TradeMode;
  amount: number;
  price: number;
  shares: number | null;
  status: TradeStatus;
  exit_type: string | null;
  created_at: string | null;
}

export interface TradeResponse {
  id: number;
  market_id: string;
  trade_type: TradeType;
  mode: TradeMode;
  amount: number;
  price: number;
  shares: number | null;
  status: TradeStatus;
  llm_prediction_id: number | null;
  position_id: number | null;
  exit_type: string | null;
  created_at: string | null;
}

export interface TradeListQueryParams {
  page?: number;
  per_page?: number;
  mode?: TradeMode;
}

// ============================================================================
// Prediction Types
// ============================================================================

export interface PredictionListItem {
  id: number;
  market_id: string;
  market_title: string | null;
  market_slug: string | null;
  market_yes_price: number | null;
  predicted_probability: number;
  confidence: number;
  edge: number | null;
  recommendation: string | null;
  actual_outcome: string | null;
  is_correct: boolean | null;
  created_at: string | null;
}

export interface PredictionResponse {
  id: number;
  market_id: string;
  market_title: string | null;
  predicted_probability: number;
  confidence: number;
  reasoning: string | null;
  key_assumptions: string[] | null;
  model_used: string | null;
  recommendation: string | null;
  actual_outcome: string | null;
  is_correct: boolean | null;
  validated_at: string | null;
  created_at: string | null;
}

export interface CategoryAccuracy {
  total: number;
  correct: number;
  accuracy: number;
}

export interface AccuracyStats {
  total_predictions: number;
  validated_predictions: number;
  correct_predictions: number;
  accuracy: number;
  avg_confidence: number;
  by_category: Record<string, CategoryAccuracy>;
}

export interface PredictionListQueryParams {
  page?: number;
  per_page?: number;
  validated?: boolean;
}

// ============================================================================
// Trade Sync Types (Story 5.6)
// ============================================================================

export interface SyncStatus {
  last_sync_at: string | null;
  is_syncing: boolean;
  can_sync: boolean;
  last_error: string | null;
  total_synced: number;
}

export interface SyncResult {
  new_trades: number;
  updated_trades: number;
  consistent_trades: number;
  inconsistent_trades: number;
  total_fetched: number;
  last_sync_at: string;
  error: string | null;
}

// ============================================================================
// Position Sync Types (Story 5.7)
// ============================================================================

export interface PositionSyncStatus {
  last_sync_at: string | null;
  is_syncing: boolean;
  can_sync: boolean;
  last_error: string | null;
  total_positions: number;
}

export interface PositionSyncResult {
  new_positions: number;
  updated_positions: number;
  closed_positions: number;
  unchanged_positions: number;
  total_fetched: number;
  last_sync_at: string;
  error: string | null;
}

// ============================================================================
// Exit Strategy Types (Story 10.6)
// ============================================================================

export interface ExitStrategyConfig {
  take_profit_enabled: boolean;
  take_profit_pct: number;
  stop_loss_enabled: boolean;
  stop_loss_pct: number;
  time_exit_enabled: boolean;
  time_exit_hours: number;
  signal_exit_enabled: boolean;
  exit_check_interval_minutes: number;
}

export interface ExitStrategyConfigUpdate {
  take_profit_enabled?: boolean;
  take_profit_pct?: number;
  stop_loss_enabled?: boolean;
  stop_loss_pct?: number;
  time_exit_enabled?: boolean;
  time_exit_hours?: number;
  signal_exit_enabled?: boolean;
  exit_check_interval_minutes?: number;
}

export interface ManualExitResponse {
  success: boolean;
  position_id: number;
  market_id: string;
  shares_sold: number;
  avg_price: number;
  total_value: number;
  realized_pnl: number | null;
  exit_type: string;
}
