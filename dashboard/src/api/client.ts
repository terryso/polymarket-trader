/**
 * Axios client configuration for API calls.
 *
 * This module sets up the HTTP client with interceptors for
 * error handling and request/response transformation.
 *
 * Story 7.6: 前端 API 集成
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';

// API base URL from environment variable
// Default to empty string to use relative paths (proxy in dev, same origin in prod)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const API_TIMEOUT = 60000; // 60 seconds (increased for sync operations)

// Error response type from backend
export interface ApiError {
  code: string;
  message: string;
}

// Success response wrapper
export interface ApiResponse<T> {
  success: true;
  data: T;
}

// Error response wrapper
export interface ApiErrorResponse {
  success: false;
  error: ApiError;
}

// Paginated response
export interface PaginatedResponse<T> {
  success: true;
  data: T[];
  meta: {
    total: number;
    page: number;
    per_page: number;
  };
}

// Create axios instance
const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
client.interceptors.request.use(
  (config) => {
    // Add auth token if needed in future
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    // Transform error to consistent format
    const apiError: ApiError = error.response?.data?.error || {
      code: 'NETWORK_ERROR',
      message: error.message || 'Network error occurred',
    };

    // Log error for debugging
    console.error('[API Error]', apiError);

    return Promise.reject(apiError);
  }
);

/**
 * Helper function for GET requests.
 * Extracts data from the standard API response wrapper.
 *
 * @param url - API endpoint URL
 * @param config - Optional Axios request config
 * @returns The data payload from the response
 */
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await client.get<ApiResponse<T>>(url, config);
  return response.data.data;
}

/**
 * Helper function for paginated GET requests.
 * Returns the full paginated response including metadata.
 *
 * @param url - API endpoint URL
 * @param config - Optional Axios request config
 * @returns The paginated response with data array and metadata
 */
export async function getPaginated<T>(url: string, config?: AxiosRequestConfig): Promise<PaginatedResponse<T>> {
  const response = await client.get<PaginatedResponse<T>>(url, config);
  return response.data;
}

/**
 * Helper function for POST requests.
 *
 * @param url - API endpoint URL
 * @param data - Request body data
 * @param config - Optional Axios request config
 * @returns The data payload from the response
 */
export async function post<T, D = unknown>(
  url: string,
  data?: D,
  config?: AxiosRequestConfig
): Promise<T> {
  const response = await client.post<ApiResponse<T>>(url, data, config);
  return response.data.data;
}

/**
 * Helper function for PUT requests.
 *
 * @param url - API endpoint URL
 * @param data - Request body data
 * @param config - Optional Axios request config
 * @returns The data payload from the response
 */
export async function put<T, D = unknown>(
  url: string,
  data?: D,
  config?: AxiosRequestConfig
): Promise<T> {
  const response = await client.put<ApiResponse<T>>(url, data, config);
  return response.data.data;
}

/**
 * Helper function for DELETE requests.
 *
 * @param url - API endpoint URL
 * @param config - Optional Axios request config
 * @returns The data payload from the response
 */
export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await client.delete<ApiResponse<T>>(url, config);
  return response.data.data;
}

export { client, API_BASE_URL };
