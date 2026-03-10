import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSystemStatus } from "@/hooks/useStatistics";
import { updateTradingState } from "@/api/statistics";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { Power, RotateCcw, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export const TradingControl = () => {
  const queryClient = useQueryClient();
  const { data: status, isLoading } = useSystemStatus();

  // Trading state toggle mutation
  const toggleTradingMutation = useMutation({
    mutationFn: (enabled: boolean) => updateTradingState(enabled, undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["statistics", "status"] });
    },
  });

  // Reset daily PnL mutation
  const resetPnLMutation = useMutation({
    mutationFn: () => updateTradingState(undefined, 0),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["statistics", "status"] });
    },
  });

  const handleToggleTrading = (enabled: boolean) => {
    toggleTradingMutation.mutate(enabled);
  };

  const handleResetPnL = () => {
    if (confirm("确定要重置每日盈亏为 0 吗？这将清除今日的累计亏损记录。")) {
      resetPnLMutation.mutate();
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const tradingEnabled = status?.trading_enabled ?? false;
  const dailyPnL = status?.daily_pnl ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Power className="h-5 w-5" />
          交易控制
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Trading Status Alert */}
        <Alert variant={tradingEnabled ? "default" : "destructive"}>
          {tradingEnabled ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          <AlertDescription>
            {tradingEnabled ? "交易已启用，系统正常运行" : "交易已暂停，新交易被阻止"}
          </AlertDescription>
        </Alert>

        {/* Trading Toggle */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <label className="text-sm font-medium">启用交易</label>
            <p className="text-xs text-muted-foreground">
              {tradingEnabled ? "系统将执行新交易" : "系统不会执行新交易"}
            </p>
          </div>
          <Switch
            checked={tradingEnabled}
            onCheckedChange={handleToggleTrading}
            disabled={toggleTradingMutation.isPending}
          />
        </div>

        {/* Daily PnL Display */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <label className="text-sm font-medium">每日盈亏</label>
            <p className="text-xs text-muted-foreground">
              {dailyPnL >= 0 ? `+$${dailyPnL.toFixed(2)}` : `-$${Math.abs(dailyPnL).toFixed(2)}`}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetPnL}
            disabled={resetPnLMutation.isPending}
          >
            {resetPnLMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <RotateCcw className="h-4 w-4 mr-1" />
                重置
              </>
            )}
          </Button>
        </div>

        {/* Additional Info */}
        <div className="pt-2 border-t space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">当前资金</span>
            <span className="font-medium">${status?.current_capital?.toFixed(2) ?? "-"}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">连续亏损</span>
            <span className="font-medium">{status?.consecutive_losses ?? 0} 次</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">降级模式</span>
            <span className="font-medium">{status?.reduced_mode ? "是" : "否"}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
