import { motion } from 'framer-motion';

interface PieceProps {
  id: string;
  player: number;
}

const PLAYER_COLORS = [
  'bg-red-600',    // Top / P1
  'bg-yellow-500', // Left / P2
  'bg-blue-600',   // Bottom / P3
  'bg-emerald-600' // Right / P4
];

export function Piece({ id, player }: PieceProps) {
  return (
    <motion.div
      layoutId={id}
      draggable={false}
      onContextMenu={(e) => e.preventDefault()}
      transition={{
        type: 'spring',
        stiffness: 400,
        damping: 30,
        mass: 1.2
      }}
      className={`relative w-[28%] aspect-square sm:w-[32%] rounded-full shadow-lg z-10 flex items-center justify-center border-[1.5px] border-white/90 cursor-pointer touch-none ${PLAYER_COLORS[player]}`}
      style={{
        boxShadow: '0 2px 4px rgba(0,0,0,0.5), inset 0 2px 4px rgba(255,255,255,0.4)',
      }}
    >
      {/* Inner reflection dot for a 3D Gotî look */}
      <div className="absolute top-[10%] left-[10%] w-[35%] h-[35%] rounded-full bg-white/40" />
    </motion.div>
  );
}
