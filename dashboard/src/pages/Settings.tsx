import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { mockSettings } from "@/data/mockData";
import { Shield, Key, BarChart3, Download, FileText, ToggleLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

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
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">设置</h2>
          <p className="text-sm text-muted-foreground mt-1">系统配置与风控参数</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SettingSection icon={<Shield className="h-4 w-4" />} title="风险控制">
            <SettingRow label="初始资金" value={`$${mockSettings.risk.initialCapital}`} />
            <SettingRow label="单笔最大" value={`${mockSettings.risk.maxPositionSize}%`} />
            <SettingRow label="置信度门槛" value={`${mockSettings.risk.confidenceThreshold}%`} />
            <SettingRow label="日亏损上限" value={`${mockSettings.risk.dailyLossLimit}%`} />
          </SettingSection>

          <SettingSection icon={<Key className="h-4 w-4" />} title="API 配置">
            <SettingRow label="LLM API" value={mockSettings.api.llmKey} />
            <SettingRow label="模型" value={mockSettings.api.model} />
            <SettingRow label="Proxy Wallet" value={mockSettings.api.proxyWallet} />
          </SettingSection>

          <SettingSection icon={<BarChart3 className="h-4 w-4" />} title="市场筛选">
            <SettingRow label="最小流动性" value={`$${mockSettings.market.minLiquidity.toLocaleString()}`} />
            <SettingRow label="最小截止天数" value={`${mockSettings.market.minDaysToExpiry} 天`} />
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
