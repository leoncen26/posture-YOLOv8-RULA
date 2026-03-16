/**
 * useWebcam Custom Hook
 *
 * Purpose:
 * Manages backend camera connection for video streaming.
 * Provides state management for video URL and backend communication.
 *
 * Returns:
 * @returns {Object} Hook state and methods
 *   - {string|null} videoUrl - The backend video stream URL
 *   - {boolean} isActive - Whether the webcam is currently active
 *   - {boolean} isLoading - Whether the webcam is initializing
 *   - {string|null} error - Any error message from backend
 *   - {Function} toggleWebcam - Function to start/stop the webcam
 *
 * Usage Example:
 * const { videoUrl, isActive, toggleWebcam } = useWebcam();
 */

import { useState, useCallback } from 'react';
import { API_ENDPOINTS } from '../config/api';

const useWebcam = () => {
  // State management for webcam functionality
  const [videoUrl, setVideoUrl] = useState(null);
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Start Webcam Function
   * Calls backend /start endpoint to activate camera
   */
  const startWebcam = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Call backend to start the camera
      const response = await fetch(`${API_ENDPOINTS.root}start`, {
        method: 'POST',
      });

      const data = await response.json();

      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to start camera');
      }

      // Set the video URL to the backend stream endpoint
      setVideoUrl(API_ENDPOINTS.video);
      setIsActive(true);
      setIsLoading(false);
    } catch (err) {
      console.error('Error starting webcam:', err);
      setError(err.message || 'Failed to connect to backend');
      setIsLoading(false);
      setIsActive(false);
    }
  }, []);

  /**
   * Stop Webcam Function
   * Calls backend /stop endpoint to release camera
   * This will turn off the camera light
   */
  const stopWebcam = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Call backend to stop the camera
      const response = await fetch(`${API_ENDPOINTS.root}stop`, {
        method: 'POST',
      });

      const data = await response.json();

      if (!response.ok && data.status === 'error') {
        throw new Error(data.message || 'Failed to stop camera');
      }

      // Clear the video URL and set inactive
      setVideoUrl(null);
      setIsActive(false);
      setIsLoading(false);
    } catch (err) {
      console.error('Error stopping webcam:', err);
      // Even if there's an error, we still stop showing the video
      setVideoUrl(null);
      setIsActive(false);
      setIsLoading(false);
    }
  }, []);

  /**
   * Toggle Webcam Function
   * Starts the webcam if inactive, stops if active
   */
  const toggleWebcam = useCallback(() => {
    if (isActive) {
      stopWebcam();
    } else {
      startWebcam();
    }
  }, [isActive, startWebcam, stopWebcam]);

  // Return hook interface
  return {
    videoUrl,
    isActive,
    isLoading,
    error,
    toggleWebcam,
  };
};

export default useWebcam;
