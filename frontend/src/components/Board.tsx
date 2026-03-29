import { Piece } from './Piece';

const BOARD_SIZE = 5;
const SAFE_ZONES = [
  '0,2', '2,0', '4,2', '2,4', '2,2'
];

interface BoardProps {
  gameState: any;
  myPlayerId: number | null;
  onCellClick?: (row: number, col: number) => void;
}

const PLAYER_STARTS = [
  [0, 2], // P1
  [2, 0], // P2
  [4, 2], // P3
  [2, 4]  // P4 - Shifted to Right-middle physically perfectly mirroring the other 3!
];

export function Board({ gameState, onCellClick }: BoardProps) {
  const grid = [];

  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) {
      const isSafe = SAFE_ZONES.includes(`${r},${c}`);
      let bgClass = 'bg-white';

      // Home base distinct colors based on symmetric edge positions
      if (r === 0 && c === 2) bgClass = 'home-0'; // Top (Red)
      else if (r === 2 && c === 0) bgClass = 'home-1'; // Left (Yellow)
      else if (r === 4 && c === 2) bgClass = 'home-2'; // Bottom (Blue)
      else if (r === 2 && c === 4) bgClass = 'home-3'; // Right (Green) - Perfectly symmetric!
      else if (r === 2 && c === 2) bgClass = 'center-zone'; // Center
      else if (isSafe) bgClass = 'safe-zone';

      // Find pieces precisely mathematically matching this cell
      const piecesInCell: any[] = [];
      if (gameState) {
        gameState.players.forEach((player: any) => {
          player.pieces.forEach((piece: any) => {
            let pieceRow = -1;
            let pieceCol = -1;

            if (piece.state === 'HOME') {
              pieceRow = PLAYER_STARTS[player.id][0];
              pieceCol = PLAYER_STARTS[player.id][1];
            } else if (piece.state === 'ON_BOARD' && piece.position) {
              pieceRow = piece.position[0];
              pieceCol = piece.position[1];
            }

            if (pieceRow === r && pieceCol === c) {
              piecesInCell.push({
                id: `p${player.id}-${piece.piece_id}`,
                playerId: player.id,
                pieceId: piece.piece_id
              });
            }
          });
        });
      }

      grid.push(
        <div
          key={`${r}-${c}`}
          className={`board-cell ${bgClass} rounded-lg shadow-inner flex flex-wrap place-content-center gap-[2px] p-[2px]`}
          onClick={() => onCellClick && onCellClick(r, c)}
        >
          {/* Framer Motion layoutId perfectly interpolates jumps. Text stripped per user direction. */}
          {piecesInCell.map(occ => (
            <Piece
              key={occ.id}
              id={occ.id}
              player={occ.playerId}
            />
          ))}

          {/* Draw a subtle X for safe zones that are empty to mark cross intersections visually */}
          {isSafe && piecesInCell.length === 0 && !(r === 0 && c === 2) && !(r === 2 && c === 0) && !(r === 4 && c === 2) && !(r === 2 && c === 4) && !(r === 2 && c === 2) && (
            <div className="absolute inset-0 flex items-center justify-center opacity-30 pointer-events-none p-2">
              <svg viewBox="0 0 100 100" className="w-full h-full text-slate-500">
                <line x1="20" y1="20" x2="80" y2="80" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
                <line x1="80" y1="20" x2="20" y2="80" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
              </svg>
            </div>
          )}
        </div>
      );
    }
  }

  return (
    <div 
      className="w-full max-w-[500px] p-2 sm:p-4 bg-slate-300 rounded-[2rem] shadow-[0_15px_40px_-10px_rgba(0,0,0,0.3)] border-[8px] border-slate-400"
      onContextMenu={(e) => e.preventDefault()}
    >
      <div className="grid grid-cols-5 gap-[2px] sm:gap-2 p-1 sm:p-2 bg-slate-500 rounded-2xl select-none" draggable={false}>
        {grid}
      </div>
    </div>
  );
}
