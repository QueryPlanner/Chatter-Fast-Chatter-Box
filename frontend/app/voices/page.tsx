'use client';

import React, { useState, useRef } from 'react';
import useSWR from 'swr';
import { getVoices, uploadVoice, deleteVoice, setDefaultVoice, VoicesResponse } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

function formatBytes(bytes: number, decimals = 2) {
  if (!+bytes) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export default function VoicesManagerPage() {
  const { data: voicesData, mutate, error } = useSWR<VoicesResponse>('/voices', getVoices);
  const [uploading, setUploading] = useState(false);
  const [voiceName, setVoiceName] = useState('');
  const [voiceFile, setVoiceFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!voiceName || !voiceFile) {
      alert('Please provide both a name and an audio file.');
      return;
    }
    setUploading(true);
    try {
      await uploadVoice(voiceName, voiceFile);
      setVoiceName('');
      setVoiceFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      await mutate();
    } catch (err: any) {
      console.error('Failed to upload voice:', err);
      alert(err.response?.data?.error?.message || 'Failed to upload voice');
    } finally {
      setUploading(false);
    }
  };

  const handleSetDefault = async (name: string) => {
    try {
      await setDefaultVoice(name);
      await mutate();
    } catch (err: any) {
      console.error('Failed to set default voice:', err);
      alert('Failed to set default voice.');
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Are you sure you want to delete the voice "${name}"?`)) return;
    try {
      await deleteVoice(name);
      await mutate();
    } catch (err: any) {
      console.error('Failed to delete voice:', err);
      alert('Failed to delete voice.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold text-text-main mb-8">Voices Manager</h1>

      <Card className="mb-12">
        <h2 className="text-xl font-semibold mb-4 text-text-main">Upload New Voice</h2>
        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-main mb-1">Voice Name</label>
            <Input
              type="text"
              value={voiceName}
              onChange={(e) => setVoiceName(e.target.value)}
              placeholder="e.g. My Custom Voice"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-main mb-1">Audio File</label>
            <Input
              type="file"
              accept="audio/*"
              ref={fileInputRef}
              onChange={(e) => setVoiceFile(e.target.files?.[0] || null)}
              required
              className="cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-surface hover:file:bg-blue-700"
            />
          </div>
          <Button type="submit" disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload Voice'}
          </Button>
        </form>
      </Card>

      <div>
        <h2 className="text-2xl font-semibold text-text-main mb-6">Available Voices</h2>
        {error ? (
          <p className="text-red-500">Failed to load voices.</p>
        ) : !voicesData ? (
          <p className="text-text-muted animate-pulse">Loading voices...</p>
        ) : voicesData.voices.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {voicesData.voices.map((voice) => (
              <Card key={voice.name} className="flex flex-col h-full p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-text-main flex items-center gap-2">
                      {voice.name}
                      {voicesData.default_voice === voice.name && (
                        <span className="bg-primary/10 text-primary text-xs px-2 py-1 rounded-full font-medium">
                          Default
                        </span>
                      )}
                    </h3>
                    <div className="text-sm text-text-muted mt-1 space-y-1">
                      <p>Size: {formatBytes(voice.file_size)}</p>
                      {voice.created && <p>Created: {new Date(voice.created).toLocaleDateString()}</p>}
                    </div>
                  </div>
                </div>

                <div className="mb-6">
                  <audio 
                    controls 
                    src={`/api/voices/${encodeURIComponent(voice.name)}/download`} 
                    className="w-full h-10 rounded" 
                  />
                </div>

                <div className="mt-auto flex gap-3 pt-4 border-t border-border-dark">
                  {voicesData.default_voice !== voice.name && (
                    <Button
                      variant="secondary"
                      className="text-sm py-2 px-4 flex-1"
                      onClick={() => handleSetDefault(voice.name)}
                    >
                      Set as Default
                    </Button>
                  )}
                  <Button
                    variant="secondary"
                    className="text-sm py-2 px-4 text-red-600 hover:bg-red-50 hover:border-red-200"
                    onClick={() => handleDelete(voice.name)}
                  >
                    Delete
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-text-muted text-center py-12 border-2 border-dashed rounded-lg border-border-dark">
            No voices found. Upload one to get started.
          </p>
        )}
      </div>
    </div>
  );
}