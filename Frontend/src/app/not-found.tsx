import Link from "next/link";
import Image from "next/image";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#070709] text-[#E4E4E7] flex flex-col items-center justify-center font-mono px-4 text-center">
      <div className="border border-white/10 bg-[#0B0D13] p-8 max-w-md w-full flex flex-col items-center">
        <Image
          src="/logo.png"
          alt="MorphAPI"
          width={56}
          height={56}
          className="w-14 h-14 object-contain mb-4 drop-shadow-[0_0_16px_rgba(16,185,129,0.3)]"
        />
        <div className="text-xs uppercase tracking-widest text-[#EF4444] mb-3">
          [ERROR 404 // ENDPOINT_NOT_FOUND]
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white mb-2">
          PAGE NOT FOUND
        </h1>
        <p className="text-xs text-neutral-400 mb-6 leading-relaxed">
          The requested route does not exist. Only the primary MorphAPI gateway instrument is active.
        </p>
        <Link
          href="/"
          className="inline-flex items-center justify-center px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs tracking-wider uppercase transition-colors"
        >
          RETURN TO GATEWAY
        </Link>
      </div>
    </div>
  );
}
