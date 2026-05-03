import React from 'react';
import { Folder } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Folder as FolderIcon } from 'lucide-react';

interface FolderCardProps {
  folder: Folder;
  onClick: (folder: Folder) => void;
}

export function FolderCard({ folder, onClick }: FolderCardProps) {
  return (
    <Card 
      className="cursor-pointer hover:border-primary transition-colors flex items-center gap-4 p-4 !pb-4"
      onClick={() => onClick(folder)}
    >
      <FolderIcon className="w-6 h-6 text-primary flex-shrink-0" />
      <span className="font-medium text-text-main truncate" title={folder.name}>
        {folder.name}
      </span>
    </Card>
  );
}
