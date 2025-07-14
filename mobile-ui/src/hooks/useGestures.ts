import { useState, useRef, useCallback } from 'react';

interface GestureState {
  isDragging: boolean;
  dragOffset: { x: number; y: number };
  gestureType: 'neutral' | 'approve' | 'reject';
}

export const useGestures = (
  onApprove: () => void,
  onReject: () => void,
  threshold: number = 100
) => {
  const [gestureState, setGestureState] = useState<GestureState>({
    isDragging: false,
    dragOffset: { x: 0, y: 0 },
    gestureType: 'neutral'
  });

  const startPos = useRef({ x: 0, y: 0 });

  const handleStart = useCallback((clientX: number, clientY: number) => {
    startPos.current = { x: clientX, y: clientY };
    setGestureState(prev => ({ ...prev, isDragging: true }));
  }, []);

  const handleMove = useCallback((clientX: number, clientY: number) => {
    if (!gestureState.isDragging) return;

    const deltaX = clientX - startPos.current.x;
    const deltaY = clientY - startPos.current.y;

    let gestureType: 'neutral' | 'approve' | 'reject' = 'neutral';
    if (Math.abs(deltaX) > 50) {
      gestureType = deltaX > 0 ? 'approve' : 'reject';
    }

    setGestureState(prev => ({
      ...prev,
      dragOffset: { x: deltaX, y: deltaY },
      gestureType
    }));
  }, [gestureState.isDragging]);

  const handleEnd = useCallback(() => {
    const { dragOffset } = gestureState;

    if (Math.abs(dragOffset.x) > threshold) {
      if (dragOffset.x > 0) {
        onApprove();
      } else {
        onReject();
      }
    }

    setGestureState({
      isDragging: false,
      dragOffset: { x: 0, y: 0 },
      gestureType: 'neutral'
    });
  }, [gestureState.dragOffset, threshold, onApprove, onReject]);

  const gestureHandlers = {
    onTouchStart: (e: React.TouchEvent) => {
      const touch = e.touches[0];
      handleStart(touch.clientX, touch.clientY);
    },
    onTouchMove: (e: React.TouchEvent) => {
      const touch = e.touches[0];
      handleMove(touch.clientX, touch.clientY);
    },
    onTouchEnd: handleEnd,
    onMouseDown: (e: React.MouseEvent) => {
      handleStart(e.clientX, e.clientY);
    },
    onMouseMove: gestureState.isDragging ? (e: React.MouseEvent) => {
      handleMove(e.clientX, e.clientY);
    } : undefined,
    onMouseUp: handleEnd,
    onMouseLeave: handleEnd
  };

  return {
    gestureState,
    gestureHandlers,
    getTransform: () => {
      const { dragOffset } = gestureState;
      const rotation = dragOffset.x * 0.1;
      return `translateX(${dragOffset.x}px) translateY(${dragOffset.y}px) rotate(${rotation}deg)`;
    }
  };
};