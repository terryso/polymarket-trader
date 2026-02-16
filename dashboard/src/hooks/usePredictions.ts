/**
 * React Query hooks for predictions API.
 *
 * Story 7.6: 前端 API 集成
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { fetchPredictions, fetchPrediction, fetchAccuracy } from '../api/predictions';
import type {
  PredictionListItem,
  PredictionResponse,
  AccuracyStats,
  PredictionListQueryParams,
} from '../api/types';

// Query keys for cache management
export const predictionsKeys = {
  all: ['predictions'] as const,
  list: (params?: PredictionListQueryParams) =>
    [...predictionsKeys.all, 'list', params] as const,
  detail: (id: number) => [...predictionsKeys.all, 'detail', id] as const,
  accuracy: () => [...predictionsKeys.all, 'accuracy'] as const,
};

/**
 * Hook for fetching prediction history with pagination and filtering.
 * Refreshes every 60 seconds (predictions change slowly).
 *
 * @param params - Query parameters for pagination and filtering
 */
export function usePredictions(
  params: PredictionListQueryParams = {}
): UseQueryResult<
  { items: PredictionListItem[]; total: number; page: number; perPage: number },
  Error
> {
  return useQuery({
    queryKey: predictionsKeys.list(params),
    queryFn: () => fetchPredictions(params),
    refetchInterval: 60000, // Refresh every 60 seconds
    staleTime: 30000,
  });
}

/**
 * Hook for fetching prediction details by ID.
 *
 * @param predictionId - Prediction unique identifier
 */
export function usePrediction(
  predictionId: number
): UseQueryResult<PredictionResponse, Error> {
  return useQuery({
    queryKey: predictionsKeys.detail(predictionId),
    queryFn: () => fetchPrediction(predictionId),
    enabled: !!predictionId, // Only fetch if predictionId is provided
    staleTime: 60000,
  });
}

/**
 * Hook for fetching prediction accuracy statistics.
 * Refreshes every 60 seconds.
 */
export function useAccuracy(): UseQueryResult<AccuracyStats, Error> {
  return useQuery({
    queryKey: predictionsKeys.accuracy(),
    queryFn: fetchAccuracy,
    refetchInterval: 60000,
    staleTime: 30000,
  });
}
