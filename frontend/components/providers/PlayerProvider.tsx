'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface Track {
  bookId: string;
  bookTitle: string;
  chapterNumber: number;
  chapterTitle: string;
  audioUrl: string;
}

interface PlayerContextType {
  currentTrack: Track | null;
  playlist: Track[];
  playTrack: (track: Track, playlist: Track[]) => void;
  playNext: () => void;
  playPrevious: () => void;
  hasNext: boolean;
  hasPrevious: boolean;
  isPlaying: boolean;
  setIsPlaying: (playing: boolean) => void;
}

const PlayerContext = createContext<PlayerContextType | undefined>(undefined);

export function PlayerProvider({ children }: { children: ReactNode }) {
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [playlist, setPlaylist] = useState<Track[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);

  const currentIndex = currentTrack 
    ? playlist.findIndex(t => t.bookId === currentTrack.bookId && t.chapterNumber === currentTrack.chapterNumber)
    : -1;

  const hasNext = currentIndex !== -1 && currentIndex < playlist.length - 1;
  const hasPrevious = currentIndex > 0;

  const playTrack = (track: Track, newPlaylist: Track[]) => {
    setCurrentTrack(track);
    setPlaylist(newPlaylist);
    setIsPlaying(true);
  };

  const playNext = () => {
    if (hasNext) {
      setCurrentTrack(playlist[currentIndex + 1]);
      setIsPlaying(true);
    }
  };

  const playPrevious = () => {
    if (hasPrevious) {
      setCurrentTrack(playlist[currentIndex - 1]);
      setIsPlaying(true);
    }
  };

  return (
    <PlayerContext.Provider value={{
      currentTrack,
      playlist,
      playTrack,
      playNext,
      playPrevious,
      hasNext,
      hasPrevious,
      isPlaying,
      setIsPlaying
    }}>
      {children}
    </PlayerContext.Provider>
  );
}

export function usePlayer() {
  const context = useContext(PlayerContext);
  if (context === undefined) {
    throw new Error('usePlayer must be used within a PlayerProvider');
  }
  return context;
}
