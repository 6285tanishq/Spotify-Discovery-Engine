import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MusicDash — Your Personal Music Studio',
  description: 'Search any song, view lyrics with chords, and play along on Guitar, Harmonica, or Piano.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white antialiased">{children}</body>
    </html>
  );
}
