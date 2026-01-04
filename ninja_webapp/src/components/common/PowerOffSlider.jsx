/**
 * @file PowerOffSlider.jsx
 * @description V4-style slide-to-power-off component with touch support.
 * User must slide the thumb completely to the right to trigger shutdown.
 */

import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import styles from './PowerOffSlider.module.css';

function PowerOffSlider() {
    const { t } = useTranslation();
    const containerRef = useRef(null);
    const thumbRef = useRef(null);
    const [isDragging, setIsDragging] = useState(false);
    const [position, setPosition] = useState(0);
    const [textOpacity, setTextOpacity] = useState(1);
    const [isShuttingDown, setIsShuttingDown] = useState(false);
    const startXRef = useRef(0);
    const maxSlideRef = useRef(0);

    useEffect(() => {
        if (containerRef.current && thumbRef.current) {
            maxSlideRef.current = containerRef.current.clientWidth - thumbRef.current.clientWidth - 8;
        }
    }, []);

    const handleStart = (e) => {
        if (isShuttingDown) return;
        setIsDragging(true);
        const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
        startXRef.current = clientX - position;
    };

    const handleMove = (e) => {
        if (!isDragging) return;
        e.preventDefault();

        const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
        let delta = clientX - startXRef.current;

        // Clamp
        if (delta < 0) delta = 0;
        if (delta > maxSlideRef.current) delta = maxSlideRef.current;

        setPosition(delta);
        setTextOpacity(1 - delta / maxSlideRef.current);
    };

    const handleEnd = async () => {
        if (!isDragging) return;
        setIsDragging(false);

        if (position >= maxSlideRef.current * 0.9) {
            // Trigger shutdown
            setPosition(maxSlideRef.current);
            setTextOpacity(0);
            await triggerShutdown();
        } else {
            // Reset with animation
            setPosition(0);
            setTextOpacity(1);
        }
    };

    const triggerShutdown = async () => {
        if (!window.confirm(t('home.shutdownConfirm') || 'Are you sure you want to power off the robot?')) {
            setPosition(0);
            setTextOpacity(1);
            return;
        }

        setIsShuttingDown(true);
        try {
            const response = await fetch('/api/system/shutdown', { method: 'POST' });
            const data = await response.json();
            if (data.status === 'shutting_down') {
                alert(t('home.shutdownSuccess') || 'Robot is shutting down. Please wait for the light to turn off.');
            }
        } catch (error) {
            console.error('Shutdown failed:', error);
            alert(t('home.shutdownError') || 'Failed to shut down robot.');
            setPosition(0);
            setTextOpacity(1);
            setIsShuttingDown(false);
        }
    };

    useEffect(() => {
        if (isDragging) {
            document.addEventListener('mousemove', handleMove);
            document.addEventListener('mouseup', handleEnd);
            document.addEventListener('touchmove', handleMove, { passive: false });
            document.addEventListener('touchend', handleEnd);
        }

        return () => {
            document.removeEventListener('mousemove', handleMove);
            document.removeEventListener('mouseup', handleEnd);
            document.removeEventListener('touchmove', handleMove);
            document.removeEventListener('touchend', handleEnd);
        };
    }, [isDragging, position]);

    return (
        <div className={styles.sliderContainer} ref={containerRef}>
            <div className={styles.sliderTrack}>
                <span className={styles.sliderText} style={{ opacity: textOpacity }}>
                    {isShuttingDown
                        ? (t('home.shuttingDown') || 'Shutting down...')
                        : (t('home.sliderText') || 'Slide to Power Off')}
                </span>
            </div>
            <div
                ref={thumbRef}
                className={`${styles.sliderThumb} ${isDragging ? styles.dragging : ''}`}
                style={{
                    transform: `translateX(${position}px)`,
                    transition: isDragging ? 'none' : 'transform 0.3s ease'
                }}
                onMouseDown={handleStart}
                onTouchStart={handleStart}
            >
                <svg viewBox="0 0 24 24" width="24" height="24" fill="#FF3B30">
                    <path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42C17.99 7.86 19 9.81 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z" />
                </svg>
            </div>
        </div>
    );
}

export default PowerOffSlider;
