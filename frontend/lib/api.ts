import axios from 'axios';

// Create the axios instance
export const api = axios.create({
  baseURL: '/api',
});

// SWR fetcher
export const fetcher = (url: string) => api.get(url).then(res => res.data);

// Models
export interface Folder {
  id: string;
  name: string;
  parent_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookProgress {
  total_chapters: number;
  completed: number;
  failed: number;
  pending: number;
  processing: number;
  percent_complete: number;
}

export interface ChapterStatus {
  chapter_number: number;
  title: string;
  status: string;
  duration_secs?: number | null;
  error?: string | null;
  retry_count: number;
  completed_chunks: number;
  total_chunks: number;
}

export interface Book {
  id: string;
  title: string;
  status: string; // 'queued', 'processing', 'completed', 'failed', 'cancelled'
  voice: string;
  output_format: string;
  folder_id?: string | null;
  total_chapters?: number;
  progress: BookProgress;
  chapters: ChapterStatus[];
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  error?: string | null;
}

export interface Chapter {
  id: string;
  book_id: string;
  title: string;
  text_content: string;
  audio_url?: string | null;
  order_index: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Voice {
  name: string;
  filename: string;
  file_size: number;
  created?: string | null;
  exists: boolean;
}

export interface VoicesResponse {
  voices: Voice[];
  count: number;
  default_voice?: string | null;
}

// API functions

export const getFolders = async (parent_id: string = 'root'): Promise<Folder[]> => {
  const params = { parent_id };
  const res = await api.get<Folder[]>('/folders', { params });
  return res.data;
};

export const createFolder = async (name: string, parent_id?: string | null): Promise<Folder> => {
  const res = await api.post<Folder>('/folders', { name, parent_id });
  return res.data;
};

export const deleteFolder = async (id: string): Promise<void> => {
  await api.delete(`/folders/${id}`);
};

export const getBooks = async (folder_id: string = 'root'): Promise<Book[]> => {
  const params = { folder_id };
  const res = await api.get<{books: Book[], count: number}>('/books', { params });
  return res.data.books;
};

export const getBook = async (id: string): Promise<Book> => {
  const res = await api.get<Book>(`/books/${id}`);
  return res.data;
};

export interface CreateBookPayload {
  title: string;
  voice: string | null;
  output_format: string;
  folder_id?: string | null;
  chapters: {
    chapter_number: number;
    title: string | null;
    text: string;
  }[];
  config?: {
    max_sentences_per_chunk: number;
    max_chunk_chars: number;
    chunk_gap_ms: number;
  };
}

export const createBook = async (payload: CreateBookPayload | FormData): Promise<Book> => {
  const res = await api.post<Book>('/books', payload);
  return res.data;
};

export const cancelBook = async (id: string): Promise<Book> => {
  const res = await api.post<Book>(`/books/${id}/cancel`);
  return res.data;
};

export const retryBook = async (id: string): Promise<Book> => {
  const res = await api.post<Book>(`/books/${id}/retry`);
  return res.data;
};

export const getVoices = async (): Promise<VoicesResponse> => {
  const res = await api.get<VoicesResponse>('/voices');
  return res.data;
};

export const uploadVoice = async (name: string, file: File): Promise<{ message: string, voice: Voice }> => {
  const formData = new FormData();
  formData.append('voice_name', name);
  formData.append('voice_file', file);
  const res = await api.post<{ message: string, voice: Voice }>('/voices', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
};

export const deleteVoice = async (name: string): Promise<void> => {
  await api.delete(`/voices/${name}`);
};

export const setDefaultVoice = async (name: string): Promise<{ message: string, default_voice: string }> => {
  const formData = new FormData();
  formData.append('voice_name', name);
  const res = await api.post<{ message: string, default_voice: string }>('/voices/default', formData);
  return res.data;
};

export const scrapeUrl = async (url: string): Promise<{ title: string; text: string; url: string }> => {
  const res = await api.post('/scrape', { url });
  return res.data;
};
