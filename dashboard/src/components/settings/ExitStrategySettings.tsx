/**
 * Exit Strategy Settings Component.
 *
 * Provides a form to configure exit strategy parameters:
 * - Take profit toggle and percentage
 * - Stop loss toggle and percentage
 * - Time exit toggle and hours
 * - Signal exit toggle
 *
 * Story 10.6: Dashboard 退出策略管理
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { settingsApi } from "@/api/settings";
import type { ExitStrategyConfig, ExitStrategyConfigUpdate } from "@/api/types";
import { Loader2, Save, TrendingUp, TrendingDown, Clock, Signal } from "lucide-react";

interface FormState {
  take_profit_enabled: boolean;
  take_profit_pct: number;
  stop_loss_enabled: boolean;
  stop_loss_pct: number;
  time_exit_enabled: boolean;
  time_exit_hours: number;
  signal_exit_enabled: boolean;
}

export function ExitStrategySettings() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch current config
  const { data: config, isLoading } = useQuery({
    queryKey: ["exitStrategyConfig"],
    queryFn: settingsApi.getExitStrategy,
  });

  // Local form state
  const [formState, setFormState] = useState<FormState | null>(null);

  // Initialize form state when config loads
  useState(() => {
    if (config && !formState) {
      setFormState({
        take_profit_enabled: config.take_profit_enabled,
        take_profit_pct: config.take_profit_pct * 100, // Convert to percentage for display
        stop_loss_enabled: config.stop_loss_enabled,
        stop_loss_pct: Math.abs(config.stop_loss_pct) * 100, // Convert to positive percentage
        time_exit_enabled: config.time_exit_enabled,
        time_exit_hours: config.time_exit_hours,
        signal_exit_enabled: config.signal_exit_enabled,
      });
    }
  });

  // Update mutation
  const mutation = useMutation({
    mutationFn: (update: ExitStrategyConfigUpdate) => settingsApi.updateExitStrategy(update),
    onSuccess: (data: ExitStrategyConfig) => {
      queryClient.invalidateQueries({ queryKey: ["exitStrategyConfig"] });
      toast({
        title: "设置已保存",
        description: "退出策略配置已更新",
      });
      // Reset form state with new config
      setFormState({
        take_profit_enabled: data.take_profit_enabled,
        take_profit_pct: data.take_profit_pct * 100,
        stop_loss_enabled: data.stop_loss_enabled,
        stop_loss_pct: Math.abs(data.stop_loss_pct) * 100,
        time_exit_enabled: data.time_exit_enabled,
        time_exit_hours: data.time_exit_hours,
        signal_exit_enabled: data.signal_exit_enabled,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "保存失败",
        description: error.message || "保存设置时发生错误",
        variant: "destructive",
      });
    },
  });

  // Loading state
  if (isLoading || !config) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">退出策略</CardTitle>
          <CardDescription>加载中...</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const currentForm = formState || {
    take_profit_enabled: config.take_profit_enabled,
    take_profit_pct: config.take_profit_pct * 100,
    stop_loss_enabled: config.stop_loss_enabled,
    stop_loss_pct: Math.abs(config.stop_loss_pct) * 100,
    time_exit_enabled: config.time_exit_enabled,
    time_exit_hours: config.time_exit_hours,
    signal_exit_enabled: config.signal_exit_enabled,
  };

  // Handle save
  const handleSave = () => {
    const update: ExitStrategyConfigUpdate = {
      take_profit_enabled: currentForm.take_profit_enabled,
      take_profit_pct: currentForm.take_profit_pct / 100, // Convert back to decimal
      stop_loss_enabled: currentForm.stop_loss_enabled,
      stop_loss_pct: -currentForm.stop_loss_pct / 100, // Convert back to negative decimal
      time_exit_enabled: currentForm.time_exit_enabled,
      time_exit_hours: currentForm.time_exit_hours,
      signal_exit_enabled: currentForm.signal_exit_enabled,
    };
    mutation.mutate(update);
  };

  // Check if form has changes
  const hasChanges =
    currentForm.take_profit_enabled !== config.take_profit_enabled ||
    currentForm.take_profit_pct !== config.take_profit_pct * 100 ||
    currentForm.stop_loss_enabled !== config.stop_loss_enabled ||
    currentForm.stop_loss_pct !== Math.abs(config.stop_loss_pct) * 100 ||
    currentForm.time_exit_enabled !== config.time_exit_enabled ||
    currentForm.time_exit_hours !== config.time_exit_hours ||
    currentForm.signal_exit_enabled !== config.signal_exit_enabled;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">退出策略</CardTitle>
        <CardDescription>
          配置自动和手动退出策略参数
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Take Profit */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            <TrendingUp className="h-4 w-4 mt-0.5 text-green-600" />
            <div className="space-y-0.5 flex-1">
              <Label htmlFor="take-profit" className="text-sm font-medium">
                止盈
              </Label>
              <p className="text-xs text-muted-foreground">
                盈利达到指定百分比时自动卖出
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Switch
              id="take-profit"
              checked={currentForm.take_profit_enabled}
              onCheckedChange={(checked) =>
                setFormState({ ...currentForm, take_profit_enabled: checked })
              }
            />
            <div className="flex items-center gap-1">
              <Input
                type="number"
                value={currentForm.take_profit_pct}
                onChange={(e) =>
                  setFormState({
                    ...currentForm,
                    take_profit_pct: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-16 h-8 text-right"
                min={0}
                max={100}
                step={1}
                disabled={!currentForm.take_profit_enabled}
              />
              <span className="text-sm text-muted-foreground">%</span>
            </div>
          </div>
        </div>

        {/* Stop Loss */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            <TrendingDown className="h-4 w-4 mt-0.5 text-red-600" />
            <div className="space-y-0.5 flex-1">
              <Label htmlFor="stop-loss" className="text-sm font-medium">
                止损
              </Label>
              <p className="text-xs text-muted-foreground">
                亏损达到指定百分比时自动卖出
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Switch
              id="stop-loss"
              checked={currentForm.stop_loss_enabled}
              onCheckedChange={(checked) =>
                setFormState({ ...currentForm, stop_loss_enabled: checked })
              }
            />
            <div className="flex items-center gap-1">
              <span className="text-sm text-muted-foreground">-</span>
              <Input
                type="number"
                value={currentForm.stop_loss_pct}
                onChange={(e) =>
                  setFormState({
                    ...currentForm,
                    stop_loss_pct: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-16 h-8 text-right"
                min={0}
                max={100}
                step={1}
                disabled={!currentForm.stop_loss_enabled}
              />
              <span className="text-sm text-muted-foreground">%</span>
            </div>
          </div>
        </div>

        {/* Time Exit */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            <Clock className="h-4 w-4 mt-0.5 text-yellow-600" />
            <div className="space-y-0.5 flex-1">
              <Label htmlFor="time-exit" className="text-sm font-medium">
                时间退出
              </Label>
              <p className="text-xs text-muted-foreground">
                持仓超过指定时间后自动卖出
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Switch
              id="time-exit"
              checked={currentForm.time_exit_enabled}
              onCheckedChange={(checked) =>
                setFormState({ ...currentForm, time_exit_enabled: checked })
              }
            />
            <div className="flex items-center gap-1">
              <Input
                type="number"
                value={currentForm.time_exit_hours}
                onChange={(e) =>
                  setFormState({
                    ...currentForm,
                    time_exit_hours: parseInt(e.target.value) || 0,
                  })
                }
                className="w-16 h-8 text-right"
                min={1}
                max={720}
                step={1}
                disabled={!currentForm.time_exit_enabled}
              />
              <span className="text-sm text-muted-foreground">小时</span>
            </div>
          </div>
        </div>

        {/* Signal Exit */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            <Signal className="h-4 w-4 mt-0.5 text-blue-600" />
            <div className="space-y-0.5 flex-1">
              <Label htmlFor="signal-exit" className="text-sm font-medium">
                信号反转
              </Label>
              <p className="text-xs text-muted-foreground">
                当 LLM 预测方向与持仓相反时自动卖出
              </p>
            </div>
          </div>
          <Switch
            id="signal-exit"
            checked={currentForm.signal_exit_enabled}
            onCheckedChange={(checked) =>
              setFormState({ ...currentForm, signal_exit_enabled: checked })
            }
          />
        </div>

        {/* Save Button */}
        <div className="flex justify-end pt-2">
          <Button
            onClick={handleSave}
            disabled={mutation.isPending || !hasChanges}
            size="sm"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                保存设置
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
