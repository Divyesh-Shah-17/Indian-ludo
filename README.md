🎲 Indian Ludo (Chauka Bara)
A Strategic 5x5 Spiral Board Game for Modern Multiplayer.

Indian Ludo is a high-performance digital reimagining of the ancient strategy game Chauka Bara. This project translates complex traditional board mechanics—including a unique spiral path, cowrie-shell probability math, and strategic combat—into a seamless, real-time web experience.
🚀 Key Features

    Real-time Multiplayer: Engineered with Socket.io for low-latency synchronization between all players.

    Dynamic Lobbies: Supports 2–4 players. Features a host-privileged start system and automated room locking once a session begins to ensure game integrity.

    Global Matchmaking: An "Online Mode" that allows unknown users to connect and play through a public queue system.

    Mobile-First UX: A responsive, thumb-optimized interface with fixed grid coordinates to prevent accidental dragging on touch devices.

    The Gate Rule: A strategic "kill-to-enter" requirement where players must capture an opponent's piece to unlock access to the inner 3x3 square.

🏗️ Technical Architecture
Backend (Python/Flask)

The server acts as the authoritative "Source of Truth" for the game state.

    State Management: Handles all move validations, capture logic, and the "Gate" rule enforcement.

    Dice Engine: Implements the 4-bit binary dice logic (0000=8) with randomized seed generation for fair play.

    Room Management: An in-memory lobby system that manages active sessions, player naming, and matchmaking without requiring persistent database overhead.

Frontend (React/Tailwind)

A modern, component-based UI designed for speed and visual clarity.

    Animation: Framer Motion handles the non-linear "Goti" (token) movement along the complex spiral path.

    Responsive Design: Utilizes a custom Tailwind configuration to provide a spacious, two-column layout on desktop and a focused, center-board view on mobile.

    Real-time Sync: Integrated custom hooks to listen for server-emitted events, updating the local UI state instantaneously.

📏 Game Rules

    Objective: Navigate all 4 tokens from the starting base to the goal at center square (2,2).

    Dice Math: Move based on the sum of 4 binary dice. A roll of 8 (all zeros) or 4 grants a bonus turn.

    The Spiral: Movement flows clockwise through the outer ring before spiraling into the inner ring.

    Combat: Landing on a square occupied by an opponent (outside of designated Safe Zones) sends their piece back to the start.

    Entry Requirement: A player must record at least one capture to enter the inner 3x3 grid.