'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX } from 'lucide-react';

interface AudioPlayerProps {
  src: string;
  className?: string;
}

export function AudioPlayer({ src, className = '' }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isMuted, setIsMuted] = useState(false);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateProgress = () => {
      setCurrentTime(audio.currentTime);
      setProgress((audio.currentTime / (audio.duration || 1)) * 100);
    };

    const updateDuration = () => {
      setDuration(audio.duration);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
      setCurrentTime(0);
    };

    audio.addEventListener('timeupdate', updateProgress);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateProgress);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const toggleMute = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (audioRef.current && duration) {
      const seekTime = (Number(e.target.value) / 100) * duration;
      audioRef.current.currentTime = seekTime;
      setProgress(Number(e.target.value));
      setCurrentTime(seekTime);
    }
  };

  const formatTime = (time: number) => {
    if (isNaN(time) || !isFinite(time)) return '0:00';
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`flex items-center gap-3 bg-surface-blue-light border-[1px] border-border-dark p-2 rounded-full shadow-[2px_2px_0px_rgba(31,31,31,1)] w-full md:w-80 ${className}`}>
      <audio ref={audioRef} src={src} preload="metadata" />
      
      <button 
        onClick={togglePlay}
        className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-primary text-white rounded-full border-[1px] border-border-dark shadow-[1px_1px_0px_rgba(31,31,31,1)] active:translate-y-[1px] active:shadow-none transition-all"
        aria-label={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
      </button>

      <div className="flex-1 flex items-center gap-2">
        <span className="text-xs font-medium text-text-main w-8 text-right font-mono">
          {formatTime(currentTime)}
        </span>
        
        <div className="relative flex-1 flex items-center h-4">
          <input 
            type="range" 
            min="0" 
            max="100" 
            value={progress || 0} 
            onChange={handleSeek}
            className="absolute w-full h-2 bg-white border-[1px] border-border-dark rounded-full appearance-none cursor-pointer z-10 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-[#FBBC05] [&::-webkit-slider-thumb]:border-[1px] [&::-webkit-slider-thumb]:border-border-dark [&::-webkit-slider-thumb]:rounded-full [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-[#FBBC05] [&::-moz-range-thumb]:border-[1px] [&::-moz-range-thumb]:border-border-dark [&::-moz-range-thumb]:rounded-full"
          />
          <div 
            className="absolute left-0 h-2 bg-[#FBBC05] rounded-l-full border-y-[1px] border-l-[1px] border-border-dark pointer-events-none z-0"
            style={{ width: `calc(${progress}% + 4px)` }}
          />
        </div>
        
        <span className="text-xs font-medium text-text-main w-8 font-mono">
          {formatTime(duration)}
        </span>
      </div>

      <button 
        onClick={toggleMute}
        className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-white text-text-main rounded-full border-[1px] border-border-dark shadow-[1px_1px_0px_rgba(31,31,31,1)] active:translate-y-[1px] active:shadow-none transition-all mr-1"
        aria-label={isMuted ? 'Unmute' : 'Mute'}
      >
        {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
      </button>
    </div>
  );
}
