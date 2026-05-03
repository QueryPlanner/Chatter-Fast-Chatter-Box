'use client';

import React, { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import useSWR from 'swr';
import { scrapeUrl, getVoices, createBook } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { ChevronRight, ArrowLeft, Plus, Trash2, Loader2 } from 'lucide-react';

function NewBookForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const folderId = searchParams.get('folderId') || '';

  const [step, setStep] = useState(1);

  // Step 1 State
  const [inputType, setInputType] = useState<'url' | 'text'>('url');
  const [url, setUrl] = useState('');
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState('');

  // Step 2 State
  const [bookTitle, setBookTitle] = useState('');
  const [chapters, setChapters] = useState<{ title: string; text: string }[]>([
    { title: 'Chapter 1', text: '' }
  ]);

  // Step 3 State
  const { data: voicesResponse, error: voicesError } = useSWR('voices', getVoices);
  const voices = voicesResponse?.voices;
  const defaultVoice = voicesResponse?.default_voice;
  const [voiceId, setVoiceId] = useState('');
  const [maxSentences, setMaxSentences] = useState(5);
  const [maxChunkChars, setMaxChunkChars] = useState(320);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleScrape = async () => {
    if (!url) return;
    setIsScraping(true);
    setScrapeError('');
    try {
      const res = await scrapeUrl(url);
      setBookTitle(res.title || '');
      setChapters([{ title: 'Chapter 1', text: res.text || '' }]);
      setStep(2);
    } catch (err) {
      setScrapeError('Failed to scrape URL. Please check the URL or use Raw Text.');
    } finally {
      setIsScraping(false);
    }
  };

  const handleNextToStep2 = () => {
    if (inputType === 'url') {
      handleScrape();
    } else {
      setStep(2);
    }
  };

  const addChapter = () => {
    setChapters([...chapters, { title: `Chapter ${chapters.length + 1}`, text: '' }]);
  };

  const updateChapter = (index: number, field: 'title' | 'text', value: string) => {
    const newChapters = [...chapters];
    newChapters[index][field] = value;
    setChapters(newChapters);
  };

  const removeChapter = (index: number) => {
    if (chapters.length <= 1) return;
    const newChapters = chapters.filter((_, i) => i !== index);
    setChapters(newChapters);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const payload = {
        title: bookTitle || 'Untitled Book',
        voice: voiceId || null,
        output_format: 'mp3',
        folder_id: folderId || null,
        chapters: chapters.map((c, i) => ({
          chapter_number: i + 1,
          title: c.title || null,
          text: c.text
        })),
        config: {
          max_sentences_per_chunk: maxSentences,
          max_chunk_chars: maxChunkChars,
          chunk_gap_ms: 120
        }
      };
      
      const newBook = await createBook(payload);
      router.push(`/books/${newBook.id}`);
    } catch (err) {
      console.error(err);
      alert('Failed to submit job. Please check your inputs and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="mb-8">
        <Button variant="secondary" onClick={() => router.back()} className="mb-4 flex items-center gap-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </Button>
        <h1 className="text-3xl font-bold text-text-main">Create New Book</h1>
        <div className="flex flex-wrap items-center gap-2 mt-4 text-sm text-text-muted">
          <button 
            onClick={() => setStep(1)} 
            className={`hover:text-primary transition-colors ${step === 1 ? 'text-primary font-semibold' : ''}`}
          >
            1. Source
          </button>
          <ChevronRight className="w-4 h-4 flex-shrink-0" />
          <button 
            onClick={() => {
              if (step > 1 || (inputType === 'text' && step === 1)) setStep(2);
            }} 
            className={`hover:text-primary transition-colors ${step === 2 ? 'text-primary font-semibold' : ''} ${step < 2 && inputType === 'url' ? 'cursor-not-allowed opacity-50' : ''}`}
            disabled={step < 2 && inputType === 'url'}
          >
            2. Chapters
          </button>
          <ChevronRight className="w-4 h-4 flex-shrink-0" />
          <button 
            onClick={() => {
              if (bookTitle && chapters.every(c => c.text.trim().length > 0)) setStep(3);
            }} 
            className={`hover:text-primary transition-colors ${step === 3 ? 'text-primary font-semibold' : ''} ${step < 3 ? 'cursor-not-allowed opacity-50' : ''}`}
            disabled={!bookTitle || chapters.some(c => !c.text.trim())}
          >
            3. Config
          </button>
        </div>
      </div>

      <Card className="p-6">
        {step === 1 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="flex gap-4 border-b border-border-dark pb-4">
              <button
                className={`pb-2 px-2 font-medium transition-colors ${inputType === 'url' ? 'text-primary border-b-2 border-primary' : 'text-text-muted hover:text-text-main'}`}
                onClick={() => setInputType('url')}
              >
                URL Scraping
              </button>
              <button
                className={`pb-2 px-2 font-medium transition-colors ${inputType === 'text' ? 'text-primary border-b-2 border-primary' : 'text-text-muted hover:text-text-main'}`}
                onClick={() => setInputType('text')}
              >
                Raw Text
              </button>
            </div>

            {inputType === 'url' ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-main mb-1">Article / Book URL</label>
                  <Input 
                    placeholder="https://example.com/article" 
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && url && !isScraping) {
                        handleNextToStep2();
                      }
                    }}
                    disabled={isScraping}
                  />
                  {scrapeError && <p className="text-red-500 text-sm mt-2">{scrapeError}</p>}
                </div>
                <Button onClick={handleNextToStep2} disabled={!url || isScraping} className="flex items-center gap-2">
                  {isScraping && <Loader2 className="w-4 h-4 animate-spin" />}
                  {isScraping ? 'Scraping URL...' : 'Next Step'}
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-text-muted text-sm">
                  Skip URL scraping and paste your book text manually in the next step.
                </p>
                <Button onClick={handleNextToStep2} className="flex items-center gap-2">
                  Next Step
                </Button>
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div>
              <label className="block text-sm font-medium text-text-main mb-1">Book Title</label>
              <Input 
                placeholder="Enter book title" 
                value={bookTitle}
                onChange={(e) => setBookTitle(e.target.value)}
              />
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-text-main">Chapters</h3>
                <Button variant="secondary" onClick={addChapter} className="flex items-center gap-2 text-sm py-2 px-4">
                  <Plus className="w-4 h-4" /> Add Chapter
                </Button>
              </div>
              
              {chapters.map((chapter, index) => (
                <Card key={index} className="p-4 border border-border-dark shadow-sm bg-surface">
                  <div className="flex items-start justify-between mb-4 gap-4">
                    <Input 
                      placeholder={`Chapter ${index + 1} Title (Optional)`}
                      value={chapter.title}
                      onChange={(e) => updateChapter(index, 'title', e.target.value)}
                      className="max-w-md bg-white dark:bg-gray-900"
                    />
                    {chapters.length > 1 && (
                      <Button variant="secondary" onClick={() => removeChapter(index)} className="text-red-500 hover:bg-red-50 hover:text-red-600 p-2 flex-shrink-0 transition-colors" title="Remove Chapter">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                  <textarea
                    className="w-full h-64 p-3 bg-white dark:bg-gray-900 text-text-main border border-border-dark rounded-md outline-none focus:border-primary resize-y font-mono text-sm leading-relaxed"
                    placeholder="Paste chapter text content here..."
                    value={chapter.text}
                    onChange={(e) => updateChapter(index, 'text', e.target.value)}
                  />
                </Card>
              ))}
            </div>

            <div className="flex gap-4 pt-4 border-t border-border-dark mt-6">
              <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
              <Button onClick={() => setStep(3)} disabled={!bookTitle || chapters.some(c => !c.text.trim())}>
                Next Step
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div>
              <label className="block text-sm font-medium text-text-main mb-1">Voice Configuration</label>
              {voicesError ? (
                <p className="text-red-500 text-sm">Failed to load voices.</p>
              ) : !voices ? (
                <div className="flex items-center gap-2 text-sm text-text-muted bg-surface p-3 rounded-md border border-border-dark">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" /> Loading available voices...
                </div>
              ) : (
                <select 
                  className="w-full bg-surface text-text-main border border-border-dark rounded-md p-3 outline-none focus:border-primary appearance-none cursor-pointer"
                  value={voiceId}
                  onChange={(e) => setVoiceId(e.target.value)}
                >
                  <option value="">Default Voice</option>
                  {voices.map(voice => (
                    <option key={voice.name} value={voice.name}>
                      {voice.name} {defaultVoice === voice.name ? '(Default)' : ''}
                    </option>
                  ))}
                </select>
              )}
              <p className="text-xs text-text-muted mt-2">Select the voice that will be used to narrate the book.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-surface p-4 rounded-md border border-border-dark">
                <label className="block text-sm font-medium text-text-main mb-1">Max Sentences per Chunk</label>
                <Input 
                  type="number" 
                  min={1} 
                  max={50}
                  value={maxSentences}
                  onChange={(e) => setMaxSentences(parseInt(e.target.value) || 5)}
                  className="bg-white dark:bg-gray-900"
                />
                <p className="text-xs text-text-muted mt-2">Maximum number of sentences combined into a single audio generation request.</p>
              </div>
              <div className="bg-surface p-4 rounded-md border border-border-dark">
                <label className="block text-sm font-medium text-text-main mb-1">Max Characters per Chunk</label>
                <Input 
                  type="number"
                  min={50}
                  max={1000}
                  value={maxChunkChars}
                  onChange={(e) => setMaxChunkChars(parseInt(e.target.value) || 320)}
                  className="bg-white dark:bg-gray-900"
                />
                <p className="text-xs text-text-muted mt-2">Hard limit on characters per chunk to prevent TTS model truncation errors.</p>
              </div>
            </div>

            {folderId && (
              <div>
                <label className="block text-sm font-medium text-text-main mb-1">Target Folder ID</label>
                <Input value={folderId} disabled className="bg-gray-50 text-gray-500 cursor-not-allowed border-gray-200" />
              </div>
            )}

            <div className="flex gap-4 pt-4 border-t border-border-dark mt-8">
              <Button variant="secondary" onClick={() => setStep(2)} disabled={isSubmitting}>Back</Button>
              <Button onClick={handleSubmit} disabled={isSubmitting} className="flex items-center gap-2 px-8">
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                {isSubmitting ? 'Creating Book...' : 'Submit Job'}
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export default function NewBookPage() {
  return (
    <Suspense fallback={<div className="p-8 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>}>
      <NewBookForm />
    </Suspense>
  );
}
