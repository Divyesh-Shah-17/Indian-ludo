import { motion } from 'framer-motion';

interface DiceProps {
  value: number; // 0 or 1
  isRolling: boolean;
}

export function CowrieShell({ value, isRolling }: DiceProps) {
  return (
    <motion.div
      animate={isRolling ? { 
        rotateZ: [0, -15, 15, -10, 10, 0],
        y: [0, -10, 5, -5, 0]
      } : {}}
      transition={{ duration: 0.4, ease: "easeInOut" }}
      className="w-10 h-14 relative"
      style={{ filter: "drop-shadow(1px 2px 4px rgba(0,0,0,0.3))" }}
    >
      <svg viewBox="0 0 100 140" className="w-full h-full text-slate-100 pointer-events-none">
        {/* Base Shell Shape */}
        <path 
          d="M 50 10 C 80 30, 95 60, 95 90 C 95 120, 70 135, 50 135 C 30 135, 5 120, 5 90 C 5 60, 20 30, 50 10 Z" 
          fill="currentColor" 
          stroke="#94a3b8" 
          strokeWidth="2"
        />
        
        {value === 1 ? (
          // Mouth UP
          <g>
            <path 
              d="M 47 40 C 50 60, 50 100, 47 115 C 50 118, 53 118, 53 115 C 50 100, 50 60, 53 40 C 50 37, 47 37, 47 40 Z"
              fill="#1e293b"
            />
            {/* Teeth */}
            <path d="M 47 50 L 44 50 M 47 60 L 43 60 M 47 70 L 42 70 M 47 80 L 43 80 M 47 90 L 44 90 M 47 100 L 45 100" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M 53 50 L 56 50 M 53 60 L 57 60 M 53 70 L 58 70 M 53 80 L 57 80 M 53 90 L 56 90 M 53 100 L 55 100" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />
          </g>
        ) : (
          // Mouth DOWN
          <g>
            <path d="M 50 20 C 55 50, 55 90, 50 120 C 45 90, 45 50, 50 20 Z" fill="#e2e8f0" />
            <path d="M 65 40 Q 75 70 65 100" stroke="#cbd5e1" fill="none" strokeWidth="2" />
            <path d="M 35 40 Q 25 70 35 100" stroke="#cbd5e1" fill="none" strokeWidth="2" />
          </g>
        )}
      </svg>
    </motion.div>
  );
}

interface DiceContainerProps {
  rollValue: number | null; 
  isRolling: boolean;
  onRoll: () => void;
  disabled: boolean;
  myTurn: boolean;
}

export function Dice({ rollValue, isRolling, onRoll, disabled, myTurn }: DiceContainerProps) {
  let shellValues = [1, 1, 1, 1]; 
  
  if (rollValue === 8) {
    shellValues = [0, 0, 0, 0];
  } else if (rollValue !== null) {
    shellValues = [0, 0, 0, 0];
    for (let i = 0; i < rollValue; i++) {
        shellValues[i] = 1;
    }
  } else {
    shellValues = [0, 1, 0, 1];
  }

  return (
    // Draggable Chowk container! The user can drag it around to reposition out of the way.
    <motion.div 
      drag 
      dragMomentum={false}
      whileDrag={{ scale: 1.05, boxShadow: "0px 20px 40px rgba(0,0,0,0.3)" }}
      className="flex flex-col items-center p-5 cursor-grab active:cursor-grabbing bg-white/90 backdrop-blur-md rounded-3xl border-2 border-slate-300 shadow-2xl w-[320px] fixed z-50 pointer-events-auto"
      style={{ bottom: '20px', left: '0', right: '0', margin: 'auto' }} 
    >
      <div className="w-12 h-1.5 bg-slate-300 rounded-full mb-3 mb-2 opacity-60"></div>
      <h3 className="text-sm font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.042 21.672 13.684 16.6m0 0-2.51 2.225.569-9.47 5.227 7.917-3.286-.672Zm-7.518-.267A8.25 8.25 0 1 1 20.25 10.5M8.288 14.212A5.25 5.25 0 1 1 17.25 10.5" />
        </svg>
        Drag Chowk
      </h3>
      
      <div className="flex justify-center gap-4 mb-6 bg-slate-100/50 p-4 rounded-2xl border border-slate-200">
        {shellValues.map((val, i) => (
          <CowrieShell key={i} value={val} isRolling={isRolling} />
        ))}
      </div>
      
      <div className="flex items-center gap-4 w-full justify-center px-2">
        {rollValue && !isRolling && (
          <div className="text-4xl font-black text-slate-800 bg-slate-100 w-16 h-16 flex items-center justify-center rounded-2xl shadow-inner border border-slate-300">
            {rollValue}
          </div>
        )}
        <button 
          onClick={(e) => { e.stopPropagation(); onRoll(); }}
          onPointerDown={(e) => e.stopPropagation()} // Prevent dragging when pressing button
          disabled={disabled || !myTurn || isRolling}
          className={`flex-1 py-4 rounded-2xl font-black text-lg tracking-widest transition-all ${
            myTurn && !disabled
            ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_4px_14px_0_rgba(37,99,235,0.39)] cursor-pointer active:scale-95 border-b-4 border-blue-800 active:border-b-0 active:translate-y-1'
            : 'bg-slate-300 text-slate-500 cursor-not-allowed'
          }`}
        >
          {isRolling ? 'ROLLING...' : myTurn ? 'ROLL' : 'WAIT'}
        </button>
      </div>

      {!myTurn && (
         <div className="mt-4 text-xs font-bold text-slate-400 animate-pulse tracking-widest uppercase text-center">
           Waiting for other players...
         </div>
      )}
    </motion.div>
  );
}
