/**
 * useRulaData Hook - Fetch RULA Assessment Data
 * 
 * Purpose:
 * Polls the backend /rula_data endpoint to get real-time RULA assessment scores.
 * Updates every 200ms to stay in sync with video stream processing.
 * 
 * @returns {Object} rulaData - The latest RULA assessment data
 */

import { useState, useEffect } from 'react';
import { API_ENDPOINTS } from '../config/api';

const useRulaData = (isActive) => {
  const [rulaData, setRulaData] = useState(null);

  useEffect(() => {
    if (!isActive) {
      setRulaData(null);
      return;
    }

    // Poll RULA data every 200ms (5 times per second)
    const intervalId = setInterval(async () => {
      try {
        const response = await fetch(API_ENDPOINTS.rulaData);
        if (response.ok) {
          const data = await response.json();
          setRulaData(data);
        }
      } catch (error) {
        console.error('Error fetching RULA data:', error);
      }
    }, 200);

    return () => clearInterval(intervalId);
  }, [isActive]);

  return rulaData;
};

export default useRulaData;
