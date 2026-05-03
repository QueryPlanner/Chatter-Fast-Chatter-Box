'use client';

import React, { useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Folder, Book, getFolders, getBooks, createFolder, getBook } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ChevronRight, FileAudio, FolderPlus, Plus, Play, Loader2, AlertCircle, Folder as FolderIcon } from 'lucide-react';
import { usePlayer, Track } from '@/components/providers/PlayerProvider';

// Helper to generate deterministic cover art based on title
function getCoverStyle(title: string) {
  const colors = [
    'bg-[#4285F4]', // Google Blue
    'bg-[#EA4335]', // Google Red
    'bg-[#FBBC05]', // Google Yellow
    'bg-[#34A853]', // Google Green
  ];
  
  const textColors = [
    'text-white',
    'text-white',
    'text-text-main', // Dark text for yellow
    'text-white'
  ];

  let hash = 0;
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % colors.length;
  
  return {
    bg: colors[index],
    text: textColors[index],
    letter: title.charAt(0).toUpperCase() || '?'
  };
}

export default function DashboardPage() {
  const router = useRouter();
  const [breadcrumbs, setBreadcrumbs] = useState<{ id: string | undefined; name: string }[]>([
    { id: undefined, name: 'Library' },
  ]);

  const currentFolderId = breadcrumbs[breadcrumbs.length - 1].id;

  const { data: folders, mutate: mutateFolders, error: foldersError } = useSWR<Folder[]>(
    ['folders', currentFolderId],
    () => getFolders(currentFolderId)
  );

  const { data: books, error: booksError } = useSWR<Book[]>(
    ['books', currentFolderId],
    () => getBooks(currentFolderId),
    { refreshInterval: 5000 } // Refresh library to catch processing updates
  );

  const { playTrack } = usePlayer();

  const handleQuickPlay = async (e: React.MouseEvent, bookId: string) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const bookDetails = await getBook(bookId);
      if (bookDetails.chapters) {
        const playlist = bookDetails.chapters
          .filter(c => c.status === 'completed')
          .map(c => ({
            bookId: bookDetails.id,
            bookTitle: bookDetails.title,
            chapterNumber: c.chapter_number,
            chapterTitle: c.title || `Chapter ${c.chapter_number}`,
            audioUrl: `/api/books/${bookDetails.id}/chapters/${c.chapter_number}/audio`
          }));
        
        if (playlist.length > 0) {
          playTrack(playlist[0], playlist);
        }
      }
    } catch (err) {
      console.error('Failed to quick play', err);
    }
  };

  const handleFolderClick = (folder: Folder) => {
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
  };

  const handleBreadcrumbClick = (index: number) => {
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
  };

  const handleNewFolder = async () => {
    const name = window.prompt('Enter new folder name:');
    if (name?.trim()) {
      try {
        await createFolder(name.trim(), currentFolderId);
        mutateFolders();
      } catch (error) {
        console.error('Failed to create folder:', error);
        alert('Failed to create folder. Please try again.');
      }
    }
  };

  const completedBooks = books?.filter(b => b.status === 'completed') || [];
  const processingBooks = books?.filter(b => b.status === 'processing' || b.status === 'queued') || [];
  const failedBooks = books?.filter(b => b.status === 'failed') || [];

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-4xl font-bold text-text-main mb-2 font-google">Your Audiobooks</h1>
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 text-text-muted flex-wrap">
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={crumb.id || 'root'}>
                <button
                  onClick={() => handleBreadcrumbClick(index)}
                  className={`hover:text-primary transition-colors text-sm font-medium ${
                    index === breadcrumbs.length - 1 ? 'text-text-main bg-surface-warm px-2 py-0.5 rounded-md border border-border-dark' : ''
                  }`}
                >
                  {crumb.name}
                </button>
                {index < breadcrumbs.length - 1 && <ChevronRight className="w-4 h-4 flex-shrink-0" />}
              </React.Fragment>
            ))}
          </div>
        </div>

        <div className="flex gap-4">
          <Button variant="secondary" onClick={handleNewFolder} className="flex items-center gap-2 bg-white hover:bg-gray-50 border-[2px] border-border-dark shadow-[2px_2px_0px_rgba(31,31,31,1)] active:translate-y-[2px] active:shadow-none transition-all">
            <FolderPlus className="w-5 h-5" />
            <span className="hidden sm:inline">New Folder</span>
          </Button>
          <Link href={`/books/new${currentFolderId ? `?folderId=${currentFolderId}` : ''}`}>
            <Button className="flex items-center gap-2 border-[2px] border-border-dark shadow-[2px_2px_0px_rgba(31,31,31,1)] active:translate-y-[2px] active:shadow-none transition-all">
              <Plus className="w-5 h-5" />
              <span className="hidden sm:inline">New Book</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Folders Section */}
      {foldersError ? (
        <p className="text-red-500 mb-8">Failed to load folders.</p>
      ) : folders === undefined ? (
        <div className="h-16 bg-gray-100 animate-pulse rounded-2xl mb-8"></div>
      ) : folders.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-12">
          {folders.map((folder) => (
            <button
              key={folder.id}
              onClick={() => handleFolderClick(folder)}
              className="flex items-center gap-3 bg-surface border-[2px] border-border-dark p-4 rounded-2xl shadow-[4px_4px_0px_rgba(31,31,31,1)] hover:translate-y-[-2px] hover:shadow-[6px_6px_0px_rgba(31,31,31,1)] active:translate-y-[2px] active:shadow-[0px_0px_0px_rgba(31,31,31,1)] transition-all text-left"
            >
              <div className="bg-surface-warm p-2 rounded-xl border border-border-dark">
                <FolderIcon className="w-6 h-6 text-text-main fill-current opacity-20" />
              </div>
              <span className="font-semibold text-text-main truncate">{folder.name}</span>
            </button>
          ))}
        </div>
      ) : null}

      {/* Main Content Split: Completed vs Processing */}
      {booksError ? (
        <p className="text-red-500">Failed to load books.</p>
      ) : books === undefined ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[1,2,3,4].map(i => <div key={i} className="h-64 bg-gray-100 animate-pulse rounded-3xl"></div>)}
        </div>
      ) : books.length > 0 ? (
        <div className="space-y-12">
          
          {/* Active / Queue Section */}
          {(processingBooks.length > 0 || failedBooks.length > 0) && (
            <div>
              <h2 className="text-2xl font-bold text-text-main mb-6 flex items-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
                Job Queue
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[...processingBooks, ...failedBooks].map(book => (
                  <Link key={book.id} href={`/books/${book.id}`}>
                    <div className="bg-surface border-[2px] border-border-dark p-5 rounded-3xl shadow-[4px_4px_0px_rgba(31,31,31,1)] hover:shadow-[6px_6px_0px_rgba(31,31,31,1)] hover:-translate-y-1 transition-all cursor-pointer h-full flex flex-col group">
                      <div className="flex justify-between items-start mb-4">
                        <div className="bg-surface-blue-light border-[2px] border-border-dark px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider text-text-main flex items-center gap-2">
                          {book.status === 'failed' ? <AlertCircle className="w-3 h-3 text-red-500" /> : <Loader2 className="w-3 h-3 animate-spin text-primary" />}
                          {book.status}
                        </div>
                      </div>
                      
                      <h3 className="text-xl font-bold text-text-main mb-4 group-hover:text-primary transition-colors line-clamp-2">
                        {book.title}
                      </h3>
                      
                      <div className="mt-auto">
                        <div className="flex justify-between text-sm font-medium mb-2 text-text-muted">
                          <span>Progress</span>
                          <span>{book.progress?.completed || 0} / {book.progress?.total_chapters || 0} Chapters</span>
                        </div>
                        <div className="w-full bg-gray-100 border-[2px] border-border-dark rounded-full h-4 overflow-hidden p-0.5">
                          <div 
                            className={`h-full rounded-full transition-all duration-500 ${book.status === 'failed' ? 'bg-red-500' : 'bg-primary'}`}
                            style={{ width: `${Math.min(100, book.progress?.percent_complete || 0)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Ready to Listen Section */}
          {completedBooks.length > 0 && (
            <div>
              <h2 className="text-2xl font-bold text-text-main mb-6 flex items-center gap-3">
                <FileAudio className="w-6 h-6 text-green-500" />
                Ready to Listen
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                {completedBooks.map(book => {
                  const cover = getCoverStyle(book.title);
                  
                  return (
                    <Link key={book.id} href={`/books/${book.id}`} className="group block">
                      <div className="bg-surface border-[2px] border-border-dark rounded-3xl shadow-[4px_4px_0px_rgba(31,31,31,1)] hover:shadow-[8px_8px_0px_rgba(31,31,31,1)] hover:-translate-y-1 transition-all overflow-hidden flex flex-col h-full">
                        {/* Generated Cover */}
                        <div className={`aspect-square w-full ${cover.bg} border-b-[2px] border-border-dark flex items-center justify-center relative overflow-hidden group-hover:opacity-90 transition-opacity`}>
                          <span className={`text-6xl font-black ${cover.text} opacity-50`}>
                            {cover.letter}
                          </span>
                          
                          {/* Quick Play Overlay */}
                          <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center backdrop-blur-sm">
                            <button 
                              onClick={(e) => handleQuickPlay(e, book.id)}
                              className="w-16 h-16 bg-primary rounded-full border-[2px] border-border-dark shadow-[4px_4px_0px_rgba(31,31,31,1)] flex items-center justify-center hover:scale-110 active:scale-95 active:translate-y-[2px] active:shadow-none transition-all"
                            >
                              <Play className="w-8 h-8 text-white fill-current ml-1" />
                            </button>
                          </div>
                        </div>
                        
                        {/* Book Metadata */}
                        <div className="p-4 flex-1 flex flex-col">
                          <h3 className="font-bold text-text-main line-clamp-2 leading-snug group-hover:text-primary transition-colors">
                            {book.title}
                          </h3>
                          <div className="mt-auto pt-3">
                            <span className="inline-block bg-surface-warm border border-border-dark px-2 py-1 rounded-md text-xs font-semibold text-text-muted">
                              {book.total_chapters} Chapters
                            </span>
                          </div>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-24 bg-surface border-[2px] border-dashed border-border-dark rounded-3xl shadow-[4px_4px_0px_rgba(31,31,31,1)]">
          <div className="w-20 h-20 bg-surface-blue-light border-[2px] border-border-dark rounded-full flex items-center justify-center mx-auto mb-6 shadow-[4px_4px_0px_rgba(31,31,31,1)] transform -rotate-6">
            <FileAudio className="w-10 h-10 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-text-main mb-3">Your library is empty</h2>
          <p className="text-text-muted mb-8 max-w-md mx-auto">
            Get started by scraping an article, uploading text, or creating a new folder to organize your audiobooks.
          </p>
          <Link href={`/books/new${currentFolderId ? `?folderId=${currentFolderId}` : ''}`}>
            <Button variant="primary" className="text-lg px-8 py-4 bg-primary text-white border-[2px] border-border-dark rounded-full shadow-[4px_4px_0px_rgba(31,31,31,1)] hover:shadow-[6px_6px_0px_rgba(31,31,31,1)] hover:-translate-y-1 active:translate-y-[2px] active:shadow-none transition-all font-bold">
              Create your first Audiobook
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
