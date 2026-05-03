'use client';

import React, { useMemo } from 'react';
import useSWR from 'swr';
import { getBook, cancelBook, retryBook } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useParams, useRouter } from 'next/navigation';
import { Download, XCircle, RefreshCw, ArrowLeft, AlertCircle, Play, Pause } from 'lucide-react';
import { usePlayer, Track } from '@/components/providers/PlayerProvider';

export default function BookDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: book, mutate, error } = useSWR(
    id ? `/books/${id}` : null,
    () => getBook(id),
    { 
      refreshInterval: (data) => (data?.status === 'processing' || data?.status === 'queued') ? 3000 : 0 
    }
  );

  const { currentTrack, isPlaying, playTrack, setIsPlaying } = usePlayer();

  const playlist: Track[] = useMemo(() => {
    if (!book || !book.chapters) return [];
    return book.chapters
      .filter(c => c.status === 'completed')
      .map(c => ({
        bookId: book.id,
        bookTitle: book.title,
        chapterNumber: c.chapter_number,
        chapterTitle: c.title || `Chapter ${c.chapter_number}`,
        audioUrl: `/api/books/${book.id}/chapters/${c.chapter_number}/audio`
      }));
  }, [book]);

  const handleCancel = async () => {
    try {
      await cancelBook(id);
      mutate();
    } catch (err) {
      console.error('Failed to cancel book:', err);
      alert('Failed to cancel book.');
    }
  };

  const handleRetry = async () => {
    try {
      await retryBook(id);
      mutate();
    } catch (err) {
      console.error('Failed to retry book:', err);
      alert('Failed to retry book.');
    }
  };

  const handlePlayChapter = (chapterNumber: number) => {
    const track = playlist.find(t => t.chapterNumber === chapterNumber);
    if (!track) return;

    if (currentTrack?.bookId === track.bookId && currentTrack?.chapterNumber === track.chapterNumber) {
      setIsPlaying(!isPlaying);
    } else {
      playTrack(track, playlist);
    }
  };

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-8 text-center">
        <h2 className="text-2xl font-bold text-red-500 mb-4">Error loading book details</h2>
        <Button onClick={() => router.back()} variant="secondary">Go Back</Button>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="h-48 bg-gray-100 rounded-xl mb-8"></div>
          <div className="h-20 bg-gray-100 rounded-xl"></div>
          <div className="h-20 bg-gray-100 rounded-xl"></div>
        </div>
      </div>
    );
  }

  const isRunning = book.status === 'processing' || book.status === 'queued';
  const hasFailed = book.progress?.failed > 0;
  const isCompleted = book.status === 'completed';

  return (
    <div className="max-w-5xl mx-auto p-8">
      <Button 
        variant="secondary" 
        onClick={() => router.push(book.folder_id ? `/?folderId=${book.folder_id}` : '/')}
        className="mb-6 flex items-center gap-2"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Library
      </Button>

      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text-main mb-3">{book.title}</h1>
          <div className="flex items-center gap-4 text-sm">
            <span className={`px-3 py-1 rounded-full font-medium capitalize ${
              book.status === 'completed' ? 'bg-green-100 text-green-800' :
              book.status === 'processing' ? 'bg-blue-100 text-blue-800' :
              book.status === 'failed' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {book.status}
            </span>
            <span className="text-text-muted border-l pl-4 border-gray-300">Voice: {book.voice}</span>
            <span className="text-text-muted border-l pl-4 border-gray-300">Format: {book.output_format.toUpperCase()}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          {isRunning && (
            <Button variant="secondary" onClick={handleCancel} className="flex items-center gap-2 bg-red-500 text-white hover:bg-red-600 border-none">
              <XCircle className="w-4 h-4" />
              Cancel Job
            </Button>
          )}
          {hasFailed && (
            <Button variant="secondary" onClick={handleRetry} className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              Retry Failed
            </Button>
          )}
          {isCompleted && (
            <a href={`/api/books/${book.id}/download`} download>
              <Button variant="primary" className="flex items-center gap-2">
                <Download className="w-4 h-4" />
                Download Full Audiobook (ZIP)
              </Button>
            </a>
          )}
        </div>
      </div>

      <Card className="p-6 mb-8 border-border-dark border shadow-sm">
        <h2 className="text-xl font-semibold mb-4 text-text-main">Overall Progress</h2>
        
        <div className="flex items-center justify-between mb-2 text-sm text-text-muted">
          <span className="font-medium text-text-main">{book.progress?.percent_complete}% Complete</span>
          <span>{book.progress?.completed} / {book.progress?.total_chapters} Chapters</span>
        </div>
        
        <div className="w-full bg-gray-200 rounded-full h-3 mb-6 overflow-hidden flex">
          {book.progress?.total_chapters > 0 && (
            <>
              <div 
                className="bg-green-500 h-full transition-all duration-500" 
                style={{ width: `${(book.progress?.completed / book.progress?.total_chapters) * 100}%` }}
                title={`Completed: ${book.progress?.completed}`}
              />
              <div 
                className="bg-blue-500 h-full transition-all duration-500" 
                style={{ width: `${(book.progress?.processing / book.progress?.total_chapters) * 100}%` }}
                title={`Processing: ${book.progress?.processing}`}
              />
              <div 
                className="bg-red-500 h-full transition-all duration-500" 
                style={{ width: `${(book.progress?.failed / book.progress?.total_chapters) * 100}%` }}
                title={`Failed: ${book.progress?.failed}`}
              />
            </>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
            <div className="text-3xl font-bold text-gray-700 mb-1">{book.progress?.pending}</div>
            <div className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Pending</div>
          </div>
          <div className="bg-blue-50 p-4 rounded-xl border border-blue-200">
            <div className="text-3xl font-bold text-blue-700 mb-1">{book.progress?.processing}</div>
            <div className="text-xs text-blue-600 uppercase tracking-wider font-semibold">Processing</div>
          </div>
          <div className="bg-green-50 p-4 rounded-xl border border-green-200">
            <div className="text-3xl font-bold text-green-700 mb-1">{book.progress?.completed}</div>
            <div className="text-xs text-green-600 uppercase tracking-wider font-semibold">Completed</div>
          </div>
          <div className="bg-red-50 p-4 rounded-xl border border-red-200">
            <div className="text-3xl font-bold text-red-700 mb-1">{book.progress?.failed}</div>
            <div className="text-xs text-red-600 uppercase tracking-wider font-semibold">Failed</div>
          </div>
        </div>
      </Card>

      <h2 className="text-2xl font-semibold mb-4 text-text-main">Chapters</h2>
      
      <div className="space-y-4">
        {book.chapters?.map((chapter) => {
          const isThisChapterPlaying = currentTrack?.bookId === book.id && currentTrack?.chapterNumber === chapter.chapter_number;
          
          return (
            <Card 
              key={chapter.chapter_number} 
              className={`p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 border-[2px] transition-colors ${
                isThisChapterPlaying ? 'border-primary bg-surface-blue-light' : 'border-border-dark bg-surface hover:bg-gray-50'
              } shadow-[2px_2px_0px_rgba(31,31,31,1)] cursor-pointer`}
              onClick={() => {
                if (chapter.status === 'completed') {
                  handlePlayChapter(chapter.chapter_number);
                }
              }}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${isThisChapterPlaying ? 'bg-primary text-white border-primary' : 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                    Ch {chapter.chapter_number}
                  </span>
                  <h3 className={`font-semibold text-lg truncate ${isThisChapterPlaying ? 'text-primary' : 'text-text-main'}`} title={chapter.title || ''}>
                    {chapter.title}
                  </h3>
                </div>
                
                <div className="flex items-center gap-4 text-sm mt-2">
                  <span className={`capitalize font-medium ${
                    chapter.status === 'completed' ? 'text-green-600' :
                    chapter.status === 'processing' ? 'text-blue-600' :
                    chapter.status === 'failed' ? 'text-red-600' :
                    'text-gray-500'
                  }`}>
                    {chapter.status}
                  </span>
                  
                  {chapter.status === 'processing' && (
                    <span className="text-text-muted flex items-center gap-1.5 bg-blue-50 px-2 py-0.5 rounded-full text-xs text-blue-700 font-medium">
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      Chunks: {chapter.completed_chunks}/{chapter.total_chunks}
                    </span>
                  )}
                  
                  {chapter.duration_secs ? (
                    <span className="text-gray-500 bg-white px-2 py-0.5 rounded-full text-xs font-medium border border-gray-200">
                      {Math.floor(chapter.duration_secs / 60)}:{(Math.floor(chapter.duration_secs) % 60).toString().padStart(2, '0')}
                    </span>
                  ) : null}
                </div>
                
                {chapter.status === 'failed' && chapter.error && (
                  <div className="mt-3 text-sm text-red-700 bg-red-50 p-3 rounded-lg border border-red-100 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span className="break-all">{chapter.error}</span>
                  </div>
                )}
              </div>

              <div className="flex-shrink-0 mt-2 md:mt-0 flex justify-end">
                {chapter.status === 'completed' && (
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePlayChapter(chapter.chapter_number);
                    }}
                    className={`w-12 h-12 flex items-center justify-center rounded-full border-[2px] border-border-dark shadow-[2px_2px_0px_rgba(31,31,31,1)] active:translate-y-[2px] active:shadow-none transition-all ${
                      isThisChapterPlaying ? 'bg-primary text-white' : 'bg-white text-text-main hover:bg-gray-100'
                    }`}
                  >
                    {isThisChapterPlaying && isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className={`w-5 h-5 fill-current ${!isThisChapterPlaying || !isPlaying ? 'ml-1' : ''}`} />}
                  </button>
                )}
              </div>
            </Card>
          );
        })}
        
        {(!book.chapters || book.chapters.length === 0) && (
          <div className="text-center py-12 text-text-muted bg-gray-50 rounded-xl border border-gray-200">
            No chapters found for this book.
          </div>
        )}
      </div>
    </div>
  );
}
