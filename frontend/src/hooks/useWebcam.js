/**
 * useWebcam Custom Hook
 *
 * Purpose:
 * Manages frontend local camera and communication with backend.
 */

import { useState, useCallback, useRef } from 'react';
import { API_ENDPOINTS } from '../config/api';

const useWebcam = () => {
  const [videoUrl, setVideoUrl] = useState(null);
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const streamRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const processingRef = useRef(false);
  const activeRef = useRef(false);

  const processFrameCycle = async () => {
    if (!activeRef.current || !videoRef.current || !canvasRef.current) return;
    
    if (processingRef.current) {
        requestAnimationFrame(processFrameCycle);
        return;
    }
    
    processingRef.current = true;
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const base64Image = canvas.toDataURL('image/jpeg', 0.5);
        
        const response = await fetch(API_ENDPOINTS.processFrame, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: base64Image })
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.image) {
            setVideoUrl(data.image);
          }
        }
      }
    } catch (e) {
      console.error('Error processing:', e);
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

      setIsActive(true);
      setIsLoading(false);
      activeRef.current = true;

      video.onloadedmetadata = () => {
        processFrameCycle();
      };
      
    } catch (err) {
      console.error('Error starting webcam:', err);
      setError(err.message || 'Failed to initialize camera');
      setIsLoading(false);
      setIsActive(false);
      activeRef.current = false;
    }
  }, []);

  const stopWebcam = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    activeRef.current = false;

    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.srcObject = null;
        videoRef.current = null;
      }
      canvasRef.current = null;

      await fetch(API_ENDPOINTS.stop, { method: 'POST' }).catch(() => {});

      setVideoUrl(null);
      setIsActive(false);
      setIsLoading(false);
    } catch (err) {
      console.error('Error stopping:', err);
      setError(err.message || 'Failed to disconnect');
      setVideoUrl(null);
      setIsActive(false);
      setIsLoading(false);
    }
  }, []);

  return {
    videoUrl,
    isActive,
    isLoading,
    error,
    toggleWebcam: isActive ? stopWebcam : startWebcam
  };
};

export default useWebcam;
