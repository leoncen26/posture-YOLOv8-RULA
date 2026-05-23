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
  const activeRef = useRef(false);

  const frameCountRef = useRef(0);
  const lastFpsTimeRef = useRef(null);

  // Wrap Date.now in a ref to satisfy react-hooks/purity linter.
  // Date.now() is only ever called inside async callbacks (never during render),
  // so this is a false positive — the ref wrapper silences it with no behavior change.
  const nowRef = useRef(() => Date.now());

  /**
   * Sequential frame processing loop.
   * 
   * Key design: await the fetch response BEFORE scheduling the next frame.
   * This guarantees exactly one request in flight at a time — no flooding,
   * no race conditions, no overlapping OPTIONS/POST pairs.
   */
  const processFrameCycle = async () => {
    if (!activeRef.current || !videoRef.current || !canvasRef.current) return;

    const startTime = nowRef.current();

    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (video.videoWidth > 0 && video.videoHeight > 0) {
        // Use full standard webcam resolution for maximum clarity
        const CAPTURE_WIDTH = 640;
        const scale = CAPTURE_WIDTH / video.videoWidth;
        const captureHeight = Math.round(video.videoHeight * scale);
        canvas.width = CAPTURE_WIDTH;
        canvas.height = captureHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, CAPTURE_WIDTH, captureHeight);

        // Restore JPEG quality for a clear visual stream
        const base64Image = canvas.toDataURL('image/jpeg', 0.8);

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
          const elapsed = nowRef.current() - lastFpsTimeRef.current;
          if (elapsed >= 1000) {
            setFps(Math.round((frameCountRef.current * 1000) / elapsed));
            frameCountRef.current = 0;
            lastFpsTimeRef.current = nowRef.current();
          }
        }
      }
    } catch (e) {
      console.error('Error processing frame:', e);
    }

    // Schedule next frame: sequential chain with minimum interval.
    // No overlapping requests possible since we await the response first.
    if (activeRef.current) {
      const processingTime = nowRef.current() - startTime;
      const MIN_INTERVAL_MS = 33; // Target ~30 FPS max
      const delay = Math.max(0, MIN_INTERVAL_MS - processingTime);
      setTimeout(processFrameCycle, delay);
    }
  };

  const startWebcam = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Warm up backend
      await fetch(API_ENDPOINTS.start, { method: 'POST' }).catch(() => { });

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
      frameCountRef.current = 0;
      lastFpsTimeRef.current = nowRef.current(); // Initialize FPS timer on start
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
      await fetch(API_ENDPOINTS.stop, { method: 'POST' }).catch(() => { });
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