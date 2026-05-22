/**
 * useWebcam Custom Hook
 *
 * Purpose:
 * Manages frontend local camera and communication with backend.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { API_ENDPOINTS } from '../config/api';

const useWebcam = () => {
  const [videoUrl, setVideoUrl] = useState(null);
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fps, setFps] = useState(0);

  const streamRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const processingRef = useRef(false);
  const activeRef = useRef(false);
  
  const frameCountRef = useRef(0);
  const lastFpsTimeRef = useRef(Date.now());
  const lastRequestTimeRef = useRef(0);

  const processFrameCycle = async () => {
    if (!activeRef.current || !videoRef.current || !canvasRef.current) return;
    
    // Target 15 FPS: Minimal interval between frames = 1000ms / 15 = ~67ms
    const MIN_INTERVAL_MS = 67; 
    const now = Date.now();
    
    if (processingRef.current || (now - lastRequestTimeRef.current < MIN_INTERVAL_MS)) {
        // Retry later
        setTimeout(() => {
          if (activeRef.current) requestAnimationFrame(processFrameCycle);
        }, 10);
        return;
    }
    
    processingRef.current = true;
    lastRequestTimeRef.current = now;
    
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // JPEG compression to save bandwidth
        const base64Image = canvas.toDataURL('image/jpeg', 0.5);
        
        const response = await fetch(API_ENDPOINTS.processFrame, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: base64Image })
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.image) {
            setVideoUrl(data.image); // Display annotated image returned by backend
          }          
          // Calculate Front-End rendering FPS 
          frameCountRef.current += 1;
          const now = Date.now();
          const elapsed = now - lastFpsTimeRef.current;
          if (elapsed >= 1000) {
            setFps(Math.round((frameCountRef.current * 1000) / elapsed));
            frameCountRef.current = 0;
            lastFpsTimeRef.current = now;
          }        }
      }
    } catch (e) {
      console.error('Error processing frame:', e);
    } finally {
      processingRef.current = false;
      if (activeRef.current) {
        requestAnimationFrame(processFrameCycle);
      }
    }
  };

  const startWebcam = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Warm up backend
      await fetch(API_ENDPOINTS.start, { method: 'POST' }).catch(() => {});

      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } 
      });
      streamRef.current = stream;

      let video = document.createElement('video');
      video.srcObject = stream;
      video.playsInline = true;
      video.muted = true;
      video.play();
      videoRef.current = video;

      let canvas = document.createElement('canvas');
      canvasRef.current = canvas;

      activeRef.current = true;
      setIsActive(true);
      setIsLoading(false);

      // Start processing loop once video is ready
      video.onloadeddata = () => {
        requestAnimationFrame(processFrameCycle);
      };
    } catch (err) {
      console.error('Error opening webcam:', err);
      setError('Failed to open local camera. Please allow permissions.');
      setIsLoading(false);
      setIsActive(false);
    }
  }, []);

  const stopWebcam = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    activeRef.current = false;
    setFps(0); // Reset FPS tracking

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
      videoRef.current = null;
    }

    try {
      await fetch(API_ENDPOINTS.stop, { method: 'POST' }).catch(() => {});
    } catch (err) {
      console.error('Error stopping webcam:', err);
    }

    setVideoUrl(null);
    setIsActive(false);
    setIsLoading(false);
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

  // Ensure camera is properly released when component unmounts
  useEffect(() => {
    return () => {
      if (activeRef.current) {
        stopWebcam();
      }
    };
  }, [stopWebcam]);

  // Return hook interface
  return {
    videoUrl,
    isActive,
    isLoading,
    error,
    fps,
    toggleWebcam,
  };
};

export default useWebcam;
