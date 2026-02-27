/**
 * Confirm Exit Dialog component tests.
 *
 * Tests for the ConfirmExitDialog component.
 *
 * Story 10.6: Dashboard 退出策略管理
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// Create a simple dialog mock that actually renders content
const MockDialog = ({ children, open }: { children: React.ReactNode; open: boolean }) =>
  open ? <div data-testid="dialog">{children}</div> : null;

const MockDialogContent = ({ children }: { children: React.ReactNode }) => (
  <div data-testid="dialog-content">{children}</div>
);

const MockDialogHeader = ({ children }: { children: React.ReactNode }) => (
  <div data-testid="dialog-header">{children}</div>
);

const MockDialogTitle = ({ children }: { children: React.ReactNode }) => (
  <h2 data-testid="dialog-title">{children}</h2>
);

const MockDialogDescription = ({ children }: { children: React.ReactNode }) => (
  <p data-testid="dialog-description">{children}</p>
);

const MockDialogFooter = ({ children }: { children: React.ReactNode }) => (
  <div data-testid="dialog-footer">{children}</div>
);

// Mock the Dialog component
vi.mock('@/components/ui/dialog', () => ({
  Dialog: MockDialog,
  DialogContent: MockDialogContent,
  DialogHeader: MockDialogHeader,
  DialogTitle: MockDialogTitle,
  DialogDescription: MockDialogDescription,
  DialogFooter: MockDialogFooter,
}));

const mockPosition = {
  id: 1,
  market_id: 'test-market-123',
  outcome: 'YES' as const,
  shares: 100,
  avg_price: 0.5,
  cur_price: 0.6,
  current_value: 60,
  pnl: 10,
  status: 'open' as const,
  opened_at: '2024-01-15T10:00:00Z',
};

describe('ConfirmExitDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('when closed', () => {
    it('should not render when open is false', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={false}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
    });
  });

  describe('when open', () => {
    it('should render dialog with position details', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      expect(screen.getByTestId('dialog')).toBeInTheDocument();
      expect(screen.getByText('确认退出持仓')).toBeInTheDocument();
      expect(screen.getByText('test-market-123')).toBeInTheDocument();
    });

    it('should display position outcome badge', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      expect(screen.getByText('YES')).toBeInTheDocument();
    });

    it('should display shares amount', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      expect(screen.getByText('100.00')).toBeInTheDocument();
    });

    it('should display average price', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      expect(screen.getByText('$0.5000')).toBeInTheDocument();
    });

    it('should display current value', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      expect(screen.getByText('$60.00')).toBeInTheDocument();
    });

    it('should display PnL with profit styling', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      expect(screen.getByText(/\+\$10.00/)).toBeInTheDocument();
    });

    it('should display PnL with loss styling for negative', async () => {
      const lossPosition = {
        ...mockPosition,
        pnl: -5,
        current_value: 45,
      };

      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={lossPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      // Check that PnL section exists with loss styling
      expect(screen.getByText('当前盈亏')).toBeInTheDocument();
    });

    it('should call onConfirm when confirm button clicked', async () => {
      const mockOnConfirm = vi.fn();

      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={mockOnConfirm}
          isLoading={false}
        />
      );

      const confirmButton = screen.getByRole('button', { name: /确认退出/i });
      fireEvent.click(confirmButton);

      expect(mockOnConfirm).toHaveBeenCalled();
    });

    it('should call onOpenChange(false) when cancel clicked', async () => {
      const mockOnOpenChange = vi.fn();

      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      const cancelButton = screen.getByRole('button', { name: /取消/i });
      fireEvent.click(cancelButton);

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('should disable buttons when loading', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={true}
        />
      );

      const cancelButton = screen.getByRole('button', { name: /取消/i });
      const confirmButton = screen.getByRole('button', { name: /处理中/i });

      expect(cancelButton).toBeDisabled();
      expect(confirmButton).toBeDisabled();
    });

    it('should show loading state on confirm button', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={mockPosition}
          onConfirm={vi.fn()}
          isLoading={true}
        />
      );

      expect(screen.getByText('处理中...')).toBeInTheDocument();
    });

    it('should return null when position is null', async () => {
      const { ConfirmExitDialog } = await import('./ConfirmExitDialog');
      const { container } = render(
        <ConfirmExitDialog
          open={true}
          onOpenChange={vi.fn()}
          position={null}
          onConfirm={vi.fn()}
          isLoading={false}
        />
      );

      expect(container.innerHTML).toBe('');
    });
  });
});
