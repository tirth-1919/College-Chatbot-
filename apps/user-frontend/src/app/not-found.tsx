import Link from "next/link";
import { AlertCircle, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] px-4 text-center">
      <div className="h-16 w-16 rounded-2xl bg-[#EF4444]/10 flex items-center justify-center text-[#EF4444] mb-6">
        <AlertCircle className="h-8 w-8" />
      </div>
      <h1 className="text-3xl font-bold tracking-tight text-[#F5F5F5] mb-2">404 - Page Not Found</h1>
      <p className="text-sm text-[#A1A1AA] max-w-md mb-8">
        The requested page does not exist or has been relocated within the college platform.
      </p>
      <Link
        href="/"
        className="px-5 py-2.5 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-white text-sm font-medium flex items-center gap-2 transition"
      >
        <ArrowLeft className="h-4 w-4" />
        Return to Home
      </Link>
    </div>
  );
}

