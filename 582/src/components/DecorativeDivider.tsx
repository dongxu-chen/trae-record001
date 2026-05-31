export default function DecorativeDivider() {
  return (
    <div className="flex items-center gap-3 py-4 px-2">
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gold-500/50 to-transparent" />
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-gold-500/60">
        <path
          d="M12 2L14 8L20 10L14 12L12 18L10 12L4 10L10 8L12 2Z"
          fill="currentColor"
          opacity="0.6"
        />
        <path
          d="M12 6L13 9L16 10L13 11L12 14L11 11L8 10L11 9L12 6Z"
          fill="currentColor"
          opacity="0.4"
        />
      </svg>
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gold-500/50 to-transparent" />
    </div>
  );
}
