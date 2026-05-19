import { Suspense } from 'react';
import DashboardContent from '@/components/DashboardContent';

function Fallback() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<Fallback />}>
      <DashboardContent />
    </Suspense>
  );
}
