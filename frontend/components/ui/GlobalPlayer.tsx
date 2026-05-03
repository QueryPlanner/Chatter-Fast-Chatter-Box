'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, Rewind, FastForward, SkipBack, SkipForward } from 'lucide-react';
import { usePlayer } from '../providers/PlayerProvider';

export function GlobalPlayer() {
  const { currentTrack, playNext, playPrevious, hasNext, hasPrevious, isPlaying, setIsPlaying } = usePlayer();
  const audioRef = useRef<HTMLAudioElement>(null);
  
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);

  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.play().catch(e => console.error("Playback prevented:", e));
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, currentTrack]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = playbackRate;
    }
  }, [playbackRate]);

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
      if (hasNext) {
        playNext();
      } else {
        setIsPlaying(false);
        setProgress(0);
        setCurrentTime(0);
      }
    };

    audio.addEventListener('timeupdate', updateProgress);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateProgress);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [hasNext, playNext, setIsPlaying]);

  // Sync isPlaying state if paused externally (e.g., media keys)
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    
    const handlePause = () => setIsPlaying(false);
    const handlePlay = () => setIsPlaying(true);
    
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('play', handlePlay);
    
    return () => {
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('play', handlePlay);
    };
  }, [setIsPlaying]);

  if (!currentTrack) return null;

  const togglePlay = () => setIsPlaying(!isPlaying);

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

  const skip = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime += seconds;
    }
  };

  const cyclePlaybackRate = () => {
    const rates = [1, 1.25, 1.5, 2];
    const currentIndex = rates.indexOf(playbackRate);
    const nextRate = rates[(currentIndex + 1) % rates.length];
    setPlaybackRate(nextRate);
  };

  const formatTime = (time: number) => {
    if (isNaN(time) || !isFinite(time)) return '0:00';
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-3xl px-4 z-50">
      <div className="bg-surface-blue-light border-[2px] border-border-dark p-4 rounded-3xl shadow-[4px_4px_0px_rgba(31,31,31,1)] flex flex-col gap-3">
        <audio ref={audioRef} src={currentTrack.audioUrl} preload="metadata" />
        
        {/* Top row: Track info & Controls */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          
          <div className="flex-1 min-w-0 text-center md:text-left">
            <h3 className="font-bold text-text-main truncate text-lg">{currentTrack.chapterTitle || `Chapter ${currentTrack.chapterNumber}`}</h3>
            <p className="text-sm text-text-muted truncate">{currentTrack.bookTitle}</p>
          </div>

          <div className="flex items-center justify-center gap-4">
            <button onClick={playPrevious} disabled={!hasPrevious} className="text-text-main disabled:opacity-30 hover:scale-110 transition-transform">
              <SkipBack className="w-5 h-5 fill-current" />
            </button>
            <button onClick={() => skip(-15)} className="text-text-main hover:scale-110 transition-transform" title="Rewind 15s">
              <Rewind className="w-5 h-5" />
            </button>
            
            <button 
              onClick={togglePlay}
              className="flex-shrink-0 w-14 h-14 flex items-center justify-center bg-primary text-white rounded-full border-[2px] border-border-dark shadow-[2px_2px_0px_rgba(31,31,31,1)] active:translate-y-[2px] active:shadow-none transition-all"
            >
              {isPlaying ? <Pause className="w-7 h-7 fill-current" /> : <Play className="w-7 h-7 fill-current ml-1" />}
            </button>

            <button onClick={() => skip(15)} className="text-text-main hover:scale-110 transition-transform" title="Forward 15s">
              <FastForward className="w-5 h-5" />
            </button>
            <button onClick={playNext} disabled={!hasNext} className="text-text-main disabled:opacity-30 hover:scale-110 transition-transform">
              <SkipForward className="w-5 h-5 fill-current" />
            </button>
          </div>

          <div className="flex-1 flex justify-end gap-3 hidden md:flex items-center">
            <button onClick={cyclePlaybackRate} className="px-2 py-1 text-sm font-bold font-mono bg-surface border-[2px] border-border-dark rounded-md shadow-[2px_2px_0px_rgba(31,31,31,1)] active:translate-y-[2px] active:shadow-none transition-all">
              {playbackRate}x
            </button>
            <button onClick={toggleMute} className="flex items-center justify-center w-10 h-10 bg-surface rounded-full border-[2px] border-border-dark shadow-[2px_2px_0px_rgba(31,31,31,1)] active:translate-y-[2px] active:shadow-none transition-all text-text-main">
              {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Bottom row: Scrubber */}
        <div className="flex items-center gap-3 w-full">
          <span className="text-xs font-medium text-text-main w-10 text-right font-mono">
            {formatTime(currentTime)}
          </span>
          
          <div className="relative flex-1 flex items-center h-4">
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={progress || 0} 
              onChange={handleSeek}
              className="absolute w-full h-2 bg-white border-[2px] border-border-dark rounded-full appearance-none cursor-pointer z-10 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:bg-[#FBBC05] [&::-webkit-slider-thumb]:border-[2px] [&::-webkit-slider-thumb]:border-border-dark [&::-webkit-slider-thumb]:rounded-full [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:bg-[#FBBC05] [&::-moz-range-thumb]:border-[2px] [&::-moz-range-thumb]:border-border-dark [&::-moz-range-thumb]:rounded-full"
            />
            <div 
              className="absolute left-0 h-2 bg-[#FBBC05] rounded-l-full border-y-[2px] border-l-[2px] border-border-dark pointer-events-none z-0"
              style={{ width: `calc(${progress}% + 4px)` }}
            />
          </div>
          
          <span className="text-xs font-medium text-text-main w-10 font-mono">
            {formatTime(duration)}
          </span>
        </div>

      </div>
    </div>
  );
}
