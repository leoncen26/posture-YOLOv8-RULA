/**
 * API Configuration
 * 
 * Central configuration for backend API endpoints.
 * Update BACKEND_URL if your Flask server runs on a different host/port.
 */

// Backend server configuration
export const BACKEND_URL = 'http://localhost:5000'; 
// API endpoints
export const API_ENDPOINTS = {
  root: `${BACKEND_URL}/`,
  video: `${BACKEND_URL}/video`,
  status: `${BACKEND_URL}/status`,
  rulaData: `${BACKEND_URL}/rula_data`,
  processFrame: `${BACKEND_URL}/process_frame`,
  start: `${BACKEND_URL}/start`,
  stop: `${BACKEND_URL}/stop`,
};

// Fetch helper with error handling
export const checkBackendStatus = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.status);
    if (!response.ok) {
      throw new Error('Backend server is not responding');
    }
    return await response.json();
  } catch (error) {
    console.error('Backend status check failed:', error);
    throw error;
  }
};

export default {
  BACKEND_URL,
  API_ENDPOINTS,
  checkBackendStatus,
};
