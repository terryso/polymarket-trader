import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useSettings } from "@/hooks/useStatistics";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Shield, Key, BarChart3, Download, FileText, ToggleLeft, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ExitStrategySettings } from "@/components/settings/ExitStrategySettings";

const SettingSection = ({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) => (
  <div className="stat-card">
    <div className="flex items-center gap-2 mb-4">
      <span className="text-primary">{icon}</span>
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
    </div>
    <div className="space-y-3">{children}</div>
  </div>
);

const SettingRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-center justify-between py-1">
    <span className="text-sm text-muted-foreground">{label}</span>
    <span className="text-sm font-mono text-foreground">{value}</span>
  </div>
);

const Settings = () => {
  const { data: settings, isLoading, error } = useSettings();

  // Loading state
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-5 w-48 mt-1" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Skeleton className="h-48" />
            <Skeleton className="h-48" />
            <Skeleton className="h-32" />
            <Skeleton className="h-48" />
          </div>
        </div>
      </DashboardLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold text-foreground">设置</h2>
            <p className="text-sm text-muted-foreground mt-1">系统配置与风控参数</p>
          </div>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              无法加载数据: {error.message}
            </AlertDescription>
          </Alert>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">设置</h2>
          <p className="text-sm text-muted-foreground mt-1">系统配置与风控参数</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SettingSection icon={<Shield className="h-4 w-4" />} title="风险控制">
            <SettingRow label="初始资金" value={`$${settings?.initial_capital ?? 0}`} />
            <SettingRow label="单笔最大" value={`${((settings?.max_single_ratio ?? 0) * 100).toFixed(0)}%`} />
            <SettingRow label="置信度门槛" value={`${((settings?.min_confidence ?? 0) * 100).toFixed(0)}%`} />
            <SettingRow label="日亏损上限" value={`${((settings?.daily_loss_limit ?? 0) * 100).toFixed(0)}%`} />
            <SettingRow label="最小边缘" value={`${((settings?.min_edge ?? 0) * 100).toFixed(0)}%`} />
            <SettingRow label="最大持仓数" value={`${settings?.max_open_markets ?? 0}`} />
          </SettingSection>

          <SettingSection icon={<Key className="h-4 w-4" />} title="API 配置">
            <SettingRow label="交易模式" value={settings?.trading_mode ?? "-"} />
            <SettingRow label="LLM 模型" value={settings?.llm_model ?? "-"} />
            <SettingRow label="LLM API" value={settings?.llm_api_base ?? "-"} />
            <SettingRow label="LLM Key" value={settings?.llm_api_key ?? "-"} />
            <SettingRow label="Proxy Wallet" value={settings?.proxy_wallet ?? "-"} />
          </SettingSection>

          {/* Story 10.6: 退出策略设置 */}
          <ExitStrategySettings />

          <SettingSection icon={<BarChart3 className="h-4 w-4" />} title="交易设置">
            <SettingRow label="交易单位" value={`$${settings?.trade_unit ?? 0}`} />
          </SettingSection>

          <div className="stat-card">
            <h3 className="text-sm font-semibold text-foreground mb-4">操作</h3>
            <div className="space-y-3">
              <Button variant="outline" className="w-full justify-start gap-2 border-border text-foreground hover:bg-accent">
                <ToggleLeft className="h-4 w-4" />
                切换 Paper/Live 模式
              </Button>
              <Button variant="outline" className="w-full justify-start gap-2 border-border text-foreground hover:bg-accent">
                <Download className="h-4 w-4" />
                导出数据
              </Button>
              <Button variant="outline" className="w-full justify-start gap-2 border-border text-foreground hover:bg-accent">
                <FileText className="h-4 w-4" />
                查看日志
              </Button>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Settings;
