import { useState, useRef, useEffect } from 'react';

interface CameraState {
  isActive: boolean;
  hasPermission: boolean;
  error: string | null;
  stream: MediaStream | null;
}

export const useCamera = () => {
  const [cameraState, setCameraState] = useState<CameraState>({
    isActive: false,
    hasPermission: false,
    error: null,
    stream: null
  });

  const videoRef = useRef<HTMLVideoElement>(null);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Use back camera
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      setCameraState({
        isActive: true,
        hasPermission: true,
        error: null,
        stream
      });
    } catch (error) {
      setCameraState(prev => ({
        ...prev,
        error: 'Camera access denied or not available',
        hasPermission: false
      }));
    }
  };

  const stopCamera = () => {
    if (cameraState.stream) {
      cameraState.stream.getTracks().forEach(track => track.stop());
    }

    setCameraState({
      isActive: false,
      hasPermission: false,
      error: null,
      stream: null
    });
  };

  const captureFrame = (): string | null => {
    if (!videoRef.current) return null;

    const canvas = document.createElement('canvas');
    const video = videoRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL('image/jpeg', 0.8);
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return {
    cameraState,
    videoRef,
    startCamera,
    stopCamera,
    captureFrame
  };
};