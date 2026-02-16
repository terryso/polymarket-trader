/**
 * React Query hooks for system status API.
 *
 * Re-exports the useSystemStatus hook from useStatistics for convenience.
 *
 * Story 7.6: 前端 API 集成
 */

export {
  useSystemStatus,
  useSettings,
  statisticsKeys as systemStatusKeys,
} from './useStatistics';
export type { SystemStatus, SanitizedSettings } from '../api/types';
