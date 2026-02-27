/**
 * API Client tests.
 *
 * Tests for the Axios client configuration including error handling.
 *
 * Story 7.6: 前端 API 集成
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';

// Mock axios
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
    },
  };
});

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetModules();
  });

  it('should create axios instance with correct configuration', async () => {
    // Import the module which will trigger axios.create
    await import('./client');

    expect(axios.create).toHaveBeenCalledWith(
      expect.objectContaining({
        timeout: 60000, // Updated to match actual client config (60 seconds)
        headers: {
          'Content-Type': 'application/json',
        },
      })
    );
  });

  it('should configure request and response interceptors', async () => {
    const { client } = await import('./client');

    expect(client.interceptors.request.use).toHaveBeenCalled();
    expect(client.interceptors.response.use).toHaveBeenCalled();
  });
});

describe('API Client Environment', () => {
  it('should use default API base URL when environment variable is not set', async () => {
    // The module should use empty string as default (relative paths)
    const { API_BASE_URL } = await import('./client');

    // Default should be empty string for proxy/same-origin requests
    expect(API_BASE_URL).toBe('');
  });
});
