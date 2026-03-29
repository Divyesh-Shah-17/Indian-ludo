import { useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import { Board } from './components/Board';
import { Dice } from './components/Dice';
import { motion, AnimatePresence } from 'framer-motion';

const SOCKET_URL = 'http://localhost:8765';

const PLAYER_STARTS = [
  [0, 2], // P1
  [2, 0], // P2
  [4, 2], // P3
  [2, 4]  // P4
];

export default function App() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [gameState, setGameState] = useState<any>(null);
  const [roomCode, setRoomCode] = useState<string>('');
  const [playerId, setPlayerId] = useState<number | null>(null);
  const [roomInfo, setRoomInfo] = useState<any>(null);
  const [inputCode, setInputCode] = useState('');

  const [rollValue, setRollValue] = useState<number | null>(null);
  const [isRolling, setIsRolling] = useState(false);
  const [errorToast, setErrorToast] = useState('');

  const [nickname, setNickname] = useState('');

  const [isSearching, setIsSearching] = useState(false);
  const [searchTime, setSearchTime] = useState(0);

  useEffect(() => {
    let interval: any;
    if (isSearching && !roomCode && !gameState) {
      interval = setInterval(() => {
        setSearchTime(prev => prev + 1);
      }, 1000);
    } else if (roomCode || gameState) {
      setIsSearching(false);
      setSearchTime(0);
    }
    return () => clearInterval(interval);
  }, [isSearching, roomCode, gameState]);

  useEffect(() => {
    const newSocket = io(SOCKET_URL, { transports: ['websocket', 'polling'] });
    setSocket(newSocket);

    newSocket.on('room_created', (data) => {
      setRoomCode(data.code);
      setPlayerId(data.player_id);
    });

    newSocket.on('room_joined', (data) => {
      setRoomCode(data.code);
      setPlayerId(data.player_id);
      if (data.room) setRoomInfo(data.room);
    });

    newSocket.on('room_updated', (data) => {
      setRoomCode(data.room.code);
      if (data.room.state === 'PLAYING') {
        // Just let game_started or state_update handle the game view
      }
      setRoomInfo(data.room);
    });

    newSocket.on('player_id_updated', (data) => {
      setPlayerId(data.player_id);
    });

    newSocket.on('game_started', (data) => {
      setGameState(data.game_state);
    });

    newSocket.on('state_update', (data) => {
      setGameState(data.game_state);
      setRollValue(null);
    });

    newSocket.on('dice_rolled', (data) => {
      setRollValue(data.value);
      setIsRolling(false);
    });

    newSocket.on('error', (data) => {
      setErrorToast(data.message);
      setIsRolling(false);
      setTimeout(() => setErrorToast(''), 3000);
    });

    return () => { newSocket.close(); };
  }, []);

  const createRoom = () => socket?.emit('create_room', { playerName: nickname });
  const joinRoom = () => socket?.emit('join_room', { code: inputCode, playerName: nickname });
  const joinPublicQueue = () => {
    socket?.emit('join_public_queue', { playerName: nickname });
    setIsSearching(true);
    setSearchTime(0);
  };

  const handleRoll = () => {
    if (!socket || !gameState || gameState.current_turn !== playerId) return;
    setIsRolling(true);
    socket.emit('roll_dice');
  };

  const handleCellClick = (row: number, col: number) => {
    if (!socket || !gameState || gameState.current_turn !== playerId || rollValue === null) return;

    // Find if the current player has a piece at this clicked location
    const me = gameState.players[playerId!];
    if (!me) return;

    // Piece position extraction
    const clickedPiece = me.pieces.find((p: any) => {
      let pieceRow = -1;
      let pieceCol = -1;
      if (p.state === 'HOME') {
        pieceRow = PLAYER_STARTS[playerId!][0];
        pieceCol = PLAYER_STARTS[playerId!][1];
      } else if (p.state === 'ON_BOARD' && p.position) {
        pieceRow = p.position[0];
        pieceCol = p.position[1];
      }
      return pieceRow === row && pieceCol === col && (p.state === 'ON_BOARD' || p.state === 'HOME');
    });

    if (clickedPiece) {
      socket.emit('move_piece', { piece_id: clickedPiece.piece_id });
    }
  };

  const handleSkip = () => {
    socket?.emit('skip_turn');
  };

  if (!gameState) {
    // Lobby UI
    return (
      <div className="min-h-screen flex items-center justify-center p-4 sm:p-8 bg-slate-100 relative overflow-hidden">
        {/* Subtle background grid pattern */}
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+CgkJPGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMSIgZmlsbD0iI2U1ZTVlNSIvPgoJPC9zdmc+')] z-0 pointer-events-none opacity-50"></div>
        
        <div className="relative z-10 max-w-6xl w-full flex flex-col lg:flex-row gap-8 lg:gap-16 items-center lg:items-stretch justify-center py-10">
            
            {/* LEFT COLUMN: Logo & Rules */}
            <div className="flex-1 flex flex-col justify-center text-center lg:text-left space-y-8 max-w-lg w-full">
               <div className="flex flex-col items-center lg:items-start">
                   <div className="w-20 h-20 bg-blue-100 text-blue-600 rounded-3xl flex items-center justify-center shadow-sm border-[4px] border-blue-200 mb-6">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
                        </svg>
                   </div>
                   <h1 className="text-5xl lg:text-7xl font-black text-slate-800 tracking-tight mb-2">Chauka Bara</h1>
                   <p className="text-xl text-slate-500 font-bold tracking-widest uppercase mb-4">Gujarati Ludo</p>
               </div>

               <div className="bg-white/80 backdrop-blur-md p-8 rounded-[2rem] border-4 border-slate-200 shadow-xl hidden sm:block">
                   <h3 className="text-xl font-black text-slate-800 tracking-widest uppercase mb-6 border-b-2 border-slate-100 pb-4">How to Play</h3>
                   <ul className="space-y-4 text-left font-bold text-slate-600">
                      <li className="flex items-start gap-4">
                         <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0 border-2 border-blue-200">1</span>
                         <span><strong className="text-slate-800">Roll the Cowries:</strong> Throw 4 cowrie shells. Rolls equal 1-4, or 8 (all face down). 4 and 8 grant an extra turn!</span>
                      </li>
                      <li className="flex items-start gap-4">
                         <span className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center flex-shrink-0 border-2 border-emerald-200">2</span>
                         <span><strong className="text-slate-800">Spiral Path:</strong> Enter the board from your home base and spiral clockwise towards the central <i>Chauka</i>.</span>
                      </li>
                      <li className="flex items-start gap-4">
                         <span className="w-8 h-8 rounded-full bg-red-100 text-red-600 flex items-center justify-center flex-shrink-0 border-2 border-red-200">3</span>
                         <span><strong className="text-slate-800">Capture to Unlock:</strong> You cannot enter the inner rings until you've successfully captured at least one opponent's piece!</span>
                      </li>
                   </ul>
               </div>
            </div>

            {/* RIGHT COLUMN: Action Card */}
            <div className="flex-1 max-w-md w-full">
                <div className="bg-white p-8 sm:p-10 lg:p-12 rounded-[2.5rem] shadow-2xl border-4 border-slate-200 text-center h-full flex flex-col justify-center">
                    
                    {roomCode ? (
                      <div className="bg-slate-50 p-6 rounded-2xl border-2 border-slate-200">
                        <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-1">Room Code</p>
                        <h2 className="text-5xl font-black text-slate-800 mb-4 tracking-widest">{roomCode}</h2>
                        
                        <div className="text-left mb-6 bg-white p-3 rounded-xl border-2 border-slate-100 shadow-sm space-y-2">
                          <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-2 border-b-2 border-slate-100 pb-2">Players Joined ({roomInfo?.player_count || 1}/4)</p>
                          {roomInfo?.players?.map((p: any, idx: number) => {
                            if (!p) return null;
                            return (
                              <div key={idx} className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-slate-100">
                                <div className="flex items-center gap-3">
                                  <div className={`w-3 h-3 rounded-full ${p.player_id === playerId ? 'bg-blue-500 animate-pulse' : 'bg-green-500'}`} />
                                  <span className="font-bold text-sm text-slate-700">{p.name || `Player ${p.player_id + 1}`}</span>
                                  {p.is_host && <span className="bg-yellow-100 text-yellow-800 text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider">Host</span>}
                                </div>
                                {p.player_id === playerId && <span className="text-[10px] font-black text-blue-400 uppercase tracking-wider">You</span>}
                              </div>
                            );
                          })}
                        </div>

                        {roomInfo?.players?.find((p: any) => p && p.player_id === playerId)?.is_host ? (
                          <button
                            onClick={() => socket?.emit('start_game')}
                            disabled={!roomInfo || roomInfo.player_count < 2}
                            className="w-full py-4 bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-300 disabled:border-b-0 disabled:translate-y-[4px] disabled:text-slate-500 text-white rounded-xl font-black tracking-widest shadow-[4px_6px_0px_#064e3b] transition-all active:scale-[0.98] active:translate-y-[4px] active:shadow-[0px_0px_0px_#064e3b] border-2 border-emerald-800"
                          >
                            START GAME
                          </button>
                        ) : (
                          <div className="flex items-center justify-center gap-2 text-blue-600 font-bold mb-2">
                            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Waiting for Host...
                          </div>
                        )}
                      </div>
                    ) : isSearching ? (
                      <div className="space-y-6 bg-slate-50 p-6 rounded-2xl border-2 border-slate-200">
                        <h2 className="text-3xl font-black text-slate-800 tracking-widest leading-tight">Searching for Players...</h2>
                        <div className="flex items-center justify-center py-4">
                          <div className="relative w-24 h-24">
                            <svg className="animate-spin w-full h-full text-emerald-500" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span className="absolute inset-0 flex items-center justify-center font-black text-2xl text-slate-700">{searchTime}s</span>
                          </div>
                        </div>
                        <p className="text-sm font-bold text-slate-500">Wait times may vary. Expanding search after 30 seconds.</p>
                      </div>
                    ) : (
                        <div className="space-y-8">
                            <div className="mb-2">
                                <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-2 text-left ml-2">Your Nickname</p>
                                <input
                                  type="text"
                                  value={nickname}
                                  onChange={(e) => setNickname(e.target.value)}
                                  placeholder="Enter Name (Optional)"
                                  className="w-full bg-slate-50 border-4 border-slate-200 rounded-2xl px-4 py-4 font-bold text-xl text-slate-700 focus:border-blue-500 focus:bg-white focus:outline-none transition-colors"
                                  maxLength={15}
                                />
                            </div>

                            <button onClick={createRoom} className="w-full py-5 bg-blue-600 hover:bg-blue-500 hover:scale-[1.02] text-white rounded-2xl font-black text-xl tracking-widest shadow-[4px_6px_0px_#1e3a8a] transition-all active:scale-[0.98] active:translate-y-[4px] active:shadow-[0px_0px_0px_#1e3a8a] border-2 border-blue-800">
                               CREATE GAME
                            </button>

                            <div className="relative flex items-center py-4">
                               <div className="flex-grow border-t border-slate-200"></div>
                               <span className="flex-shrink-0 mx-4 text-slate-300 font-bold text-xs uppercase tracking-widest">Join with Code</span>
                               <div className="flex-grow border-t border-slate-200"></div>
                            </div>
                            
                            <div className="flex gap-3">
                                <input 
                                  type="text"
                                  value={inputCode}
                                  onChange={(e) => setInputCode(e.target.value.toUpperCase())}
                                  placeholder="CODE"
                                  className="w-2/3 bg-slate-50 border-4 border-slate-200 rounded-2xl px-4 py-4 text-center font-black text-3xl uppercase tracking-widest focus:border-blue-500 focus:bg-white focus:outline-none transition-colors"
                                  maxLength={6}
                                />
                                <button onClick={joinRoom} disabled={inputCode.length < 4} className="w-1/3 bg-slate-800 hover:bg-slate-700 hover:scale-[1.02] text-white rounded-2xl font-black text-xl tracking-wider disabled:opacity-50 transition-all shadow-[4px_6px_0px_#0f172a] active:scale-[0.98] active:translate-y-[4px] active:shadow-[0px_0px_0px_#0f172a] border-2 border-slate-900">
                                   JOIN
                                </button>
                            </div>

                            <div className="relative flex items-center py-4">
                               <div className="flex-grow border-t border-slate-200"></div>
                               <span className="flex-shrink-0 mx-4 text-slate-300 font-bold text-xs uppercase tracking-widest">Or</span>
                               <div className="flex-grow border-t border-slate-200"></div>
                            </div>

                            <button onClick={joinPublicQueue} className="w-full py-5 bg-emerald-500 hover:bg-emerald-400 hover:scale-[1.02] text-white rounded-2xl font-black text-xl tracking-widest shadow-[4px_6px_0px_#064e3b] transition-all active:scale-[0.98] active:translate-y-[4px] active:shadow-[0px_0px_0px_#064e3b] border-2 border-emerald-800">
                               PLAY ONLINE
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
      </div>
    );
  }

  // Active Game UI
  const isMyTurn = gameState.current_turn === playerId;

  const getPlayerName = (pid: number) => {
    const profile = roomInfo?.players?.find((sp: any) => sp && sp.player_id === pid);
    return profile?.name || `Player ${pid + 1}`;
  };

  return (
    <div className="min-h-screen bg-slate-100 py-4 px-2 sm:px-6 relative flex flex-col items-center overflow-x-hidden">
      {/* Top Header HUD */}
      <div className="w-full max-w-[500px] flex justify-between items-center mb-6 z-10 bg-white py-4 px-4 sm:px-6 rounded-3xl shadow-lg border-4 border-slate-200 mx-auto">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-full border-4 border-slate-100 shadow-md ${['bg-red-600', 'bg-yellow-500', 'bg-blue-600', 'bg-emerald-600'][playerId!]}`} />
          <span className="font-black text-slate-800 tracking-wide text-sm sm:text-lg">You: {getPlayerName(playerId!)}</span>
        </div>

        <div className="flex items-center gap-2">
          {isMyTurn ? (
            <span className="bg-yellow-400 text-yellow-900 px-5 py-2 rounded-full text-xs font-black tracking-widest shadow-[0_0_15px_rgba(250,204,21,0.6)] border-2 border-yellow-500 vibrate">YOUR TURN</span>
          ) : (
            <div className="flex items-center gap-2 bg-slate-100 px-4 py-2 rounded-full border-2 border-slate-200 max-w-[150px] sm:max-w-none">
              <div className={`w-4 h-4 rounded-full flex-shrink-0 ${['bg-red-600', 'bg-yellow-500', 'bg-blue-600', 'bg-emerald-600'][gameState.current_turn]}`} />
              <span className="text-slate-600 font-bold text-[10px] sm:text-xs tracking-wider uppercase truncate" title={`${getPlayerName(gameState.current_turn)}'S TURN`}>
                {getPlayerName(gameState.current_turn)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main Play Area */}
      <div className="z-10 w-full max-w-[500px] flex justify-center pb-32 px-1 select-none touch-manipulation mx-auto relative">
        <Board
          gameState={gameState}
          myPlayerId={playerId}
          onCellClick={handleCellClick}
        />
      </div>

      {/* The floating, draggable Chowk Dice container */}
      <Dice
        rollValue={rollValue}
        isRolling={isRolling}
        onRoll={handleRoll}
        disabled={rollValue !== null}
        myTurn={isMyTurn}
      />

      {/* Centered Skip Action Notification */}
      <AnimatePresence>
        {isMyTurn && rollValue !== null && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.9 }}
            className="fixed bottom-6 left-0 right-0 mx-auto w-11/12 max-w-[400px] z-40 bg-slate-800 text-white p-5 rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-4 border-slate-700 flex items-center justify-between pointer-events-auto"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center border border-blue-500/50">
                👆
              </div>
              <div className="flex flex-col">
                <span className="font-black tracking-widest text-sm uppercase">Tap Piece</span>
                <span className="text-slate-400 text-xs font-bold">To move places</span>
              </div>
            </div>

            <button
              onClick={handleSkip}
              className="text-xs font-black tracking-widest text-white bg-red-600 hover:bg-red-500 border-b-4 border-red-800 active:border-b-0 active:translate-y-1 px-4 py-3 rounded-xl transition-all shadow-md"
            >
              SKIP
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Toasts */}
      <AnimatePresence>
        {errorToast && (
          <motion.div
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className="fixed top-24 bg-red-600 text-white font-black tracking-widest px-8 py-4 rounded-2xl shadow-2xl z-50 text-sm border-4 border-red-800 uppercase"
          >
            {errorToast}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Winner Overlay */}
      {gameState.winner_id !== null && gameState.winner_id !== undefined && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-4">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white rounded-3xl p-10 text-center max-w-sm w-full shadow-2xl border-8 border-yellow-400"
          >
            <div className="text-8xl mb-6">🏆</div>
            <h2 className="text-4xl font-black text-slate-800 mb-2 tracking-tight">Game Over!</h2>
            <p className="text-xl font-bold text-slate-500 mb-8 uppercase tracking-widest">
              {gameState.winner_id === playerId ? 'You won!' : `Player ${gameState.winner_id + 1} won!`}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="w-full py-5 bg-blue-600 text-white rounded-2xl font-black tracking-widest text-xl shadow-xl hover:bg-blue-500 border-b-[6px] border-blue-800 active:border-b-0 active:translate-y-[6px]"
            >
              PLAY AGAIN
            </button>
          </motion.div>
        </div>
      )}
    </div>
  );
}
