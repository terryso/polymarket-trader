/**
 * Predictions API module.
 *
 * Provides functions to fetch prediction history and accuracy statistics.
 *
 * Story 7.6: 前端 API 集成
 */

import { get, getPaginated } from './client';
import type {
  PredictionListItem,
  PredictionResponse,
  AccuracyStats,
  PredictionListQueryParams,
} from './types';

/**
 * Get prediction history with pagination and filtering.
 *
 * @param params - Query parameters for pagination and filtering
 */
export async function fetchPredictions(
  params: PredictionListQueryParams = {}
): Promise<{ items: PredictionListItem[]; total: number; page: number; perPage: number }> {
  const response = await getPaginated<PredictionListItem>('/api/predictions', {
    params: {
      page: params.page ?? 1,
      per_page: params.per_page ?? 20,
      validated: params.validated,
    },
  });
  return {
    items: response.data,
    total: response.meta.total,
    page: response.meta.page,
    perPage: response.meta.per_page,
  };
}

/**
 * Get prediction details by ID.
 *
 * @param predictionId - Prediction unique identifier
 */
export async function fetchPrediction(predictionId: number): Promise<PredictionResponse> {
  return get<PredictionResponse>(`/api/predictions/${predictionId}`);
}

/**
 * Get prediction accuracy statistics.
 */
export async function fetchAccuracy(): Promise<AccuracyStats> {
  return get<AccuracyStats>('/api/predictions/accuracy');
}

/**
 * Predictions API object with all methods.
 */
export const predictionsApi = {
  getList: fetchPredictions,
  getById: fetchPrediction,
  getAccuracy: fetchAccuracy,
};
