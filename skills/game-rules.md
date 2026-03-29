# SKILL: Gujarati_Ludo_Mechanics

## 1. Dice Probability (The Cowrie Rule)
- INPUT: 4 binary values (0 or 1).
- MATH: 
  - If sum is 0, MOVE = 8.
  - Else, MOVE = sum.
- CONSTRAINT: Rolling an 8 or a 4 grants an extra turn (traditional Chauka Bara rule).

## 2. Spiral Path System
- PATH_TYPE: Linear Array of 25 steps per player.
- LOGIC: Players share the same grid but have different `Step[0]` indices.
- ENTRY_RESTRICTION: 
  - Steps 0-15 = Outer Ring.
  - Steps 16-23 = Inner Ring.
  - Step 24 = Center (2,2).
  - FLAG: `can_enter_inner` = False by default. Set to True only after `on_capture_event`.

## 3. Capture & Safe Zones
- SAFE_ZONES: [(0,2), (2,0), (4,2), (2,4), (2,2)]
- ACTION: If Piece_A moves to (x,y) occupied by Piece_B AND (x,y) NOT IN SAFE_ZONES:
  - Piece_B.position = START
  - Piece_A.player.can_enter_inner = True