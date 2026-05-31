import { useEffect } from 'react';
import { useAppStore } from '@/store';

export default function Home() {
  const { setCurrentPage } = useAppStore();

  useEffect(() => {
    setCurrentPage('search');
  }, [setCurrentPage]);

  return null;
}
