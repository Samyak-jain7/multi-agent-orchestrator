import type { Metadata } from 'next';
import { QueryProvider } from '@/components/QueryProvider';
import './globals.css';

export const metadata: Metadata = {
  title: 'Multi-Agent Orchestrator',
  description: 'A platform to visually configure and run multiple AI agents for complex tasks',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
