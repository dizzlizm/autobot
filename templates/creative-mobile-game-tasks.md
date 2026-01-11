# Creative Mobile Game Challenge

Build an original casual mobile game for Expo/React Native. Be creative with theme, mechanics, and style. The game should be simple, addictive, and suitable for short play sessions.

---

## Task 1: Project Foundation
Initialize a new Expo project with TypeScript. Choose a creative and memorable name for your game. Set up the basic project structure with folders for components, hooks, utils, and assets. Install essential dependencies for game development (animation, sound, haptics, storage).

## Task 2: Game Concept Design
Create a GAME_DESIGN.md file documenting your creative vision. Invent an original game concept - something simple but engaging. Describe the core mechanic in one sentence. Define the theme/aesthetic (cute, retro, minimal, neon, nature, space, etc.). List what makes your game unique and fun.

## Task 3: Color Palette and Theme
Create a theme configuration file with your chosen color palette. Pick 5-7 colors that work together and match your game's mood. Define colors for: background, primary action, secondary elements, accent/highlight, text, success states, danger/warning states. Make it visually distinctive.

## Task 4: Core Game State
Build the main game state management. Decide what data your game needs to track (score, level, lives, position, velocity, inventory, etc.). Create a clean state structure that represents everything happening in your game. Include states for: menu, playing, paused, game over.

## Task 5: Game Loop Foundation
Implement the core game loop using requestAnimationFrame. Target 60fps smooth performance. The loop should update game state and trigger re-renders efficiently. Add delta time calculation for consistent physics regardless of frame rate.

## Task 6: Main Game Screen Layout
Create the primary game screen component. Design a clean layout with: game area (main focus), score display, essential UI elements. Keep it minimal - players should focus on the action. Make sure it works on different screen sizes.

## Task 7: Player Entity or Control Point
Implement whatever the player directly controls. This could be: a character, a paddle, a cannon, a finger-tracking element, a swipe zone, or something creative. Make it feel responsive and satisfying to control.

## Task 8: Core Game Mechanic - Part 1
Implement the primary action of your game. This is THE thing players do repeatedly. Examples: tap to jump, swipe to slice, drag to aim, hold to charge, tap to drop. Whatever you choose, make it feel crisp and immediate.

## Task 9: Core Game Mechanic - Part 2
Expand the core mechanic with nuance. Add timing elements, precision requirements, or risk/reward tradeoffs. The difference between a good tap and perfect tap should matter. Give skilled players room to excel.

## Task 10: Game Objects or Obstacles
Create the things the player interacts with. These could be: falling objects, approaching enemies, collectibles, platforms, targets, or hazards. Design them to create interesting decisions for the player.

## Task 11: Collision Detection
Implement collision detection between game elements. Choose appropriate hitboxes (rectangular, circular, or pixel-based). Make collisions feel fair - when players fail, they should feel it was their fault, not bad detection.

## Task 12: Scoring System
Design an interesting scoring system. Points should reflect skill. Consider: base points, combo multipliers, streak bonuses, perfect timing bonuses, or risk bonuses. Show score changes with satisfying feedback.

## Task 13: Difficulty Progression
Make the game get harder over time. This could be: faster speed, more obstacles, smaller targets, less reaction time, or new challenge types. The progression should feel gradual but noticeable.

## Task 14: Visual Feedback - Success States
Add juicy visual feedback for positive actions. When players do something good: particles, flashes, scale pops, color shifts, screen effects. Make success feel celebratory. Don't overdo it - find the right balance.

## Task 15: Visual Feedback - Failure States
Add clear feedback for mistakes or damage. Screen shake, color flash, visual glitches, or impact effects. Players should instantly know something went wrong without needing to read text.

## Task 16: Animation System
Create reusable animation utilities. Implement easing functions (ease-in, ease-out, bounce, elastic). Add helpers for common animations: fade, scale, slide, rotate. Animations should be smooth and performant.

## Task 17: Sound Effect Integration
Set up the audio system with expo-av. Create a sound manager that can play multiple sounds. Plan for: action sounds, success sounds, failure sounds, UI sounds, and ambient sounds. Even with placeholder sounds, the system should be ready.

## Task 18: Haptic Feedback
Add tactile feedback using expo-haptics. Light haptics for regular actions, medium for important events, heavy for impacts or failures. Haptics make mobile games feel more physical and satisfying.

## Task 19: Particle System
Build a simple particle system for visual effects. Particles should have: position, velocity, lifetime, color, size. Use particles for: explosions, trails, celebrations, ambient atmosphere. Keep particle count reasonable for performance.

## Task 20: Combo System
Implement a combo or streak mechanic. Consecutive successful actions should build a multiplier. Display the current combo prominently. Breaking a combo should feel significant. High combos should be exciting and rewarding.

## Task 21: Power-ups or Special Abilities
Add at least 2-3 special items or abilities. These could be: slow motion, shields, double points, magnets, size changes, or something unique to your game. Power-ups should feel impactful and change gameplay temporarily.

## Task 22: Game Over Detection
Implement game over conditions. This could be: running out of lives, missing too many objects, hitting a fatal obstacle, or time running out. The transition to game over should be clear but not jarring.

## Task 23: Game Over Screen
Create an engaging game over screen. Show: final score, high score comparison, interesting stats from the run. Include: retry button (prominent), main menu button. Maybe add a fun message based on performance.

## Task 24: High Score Persistence
Save high scores using AsyncStorage. Store at least the top 5 scores. Load scores on app start. Celebrate when players beat their high score. Consider storing additional stats for fun comparisons.

## Task 25: Main Menu Screen
Design an inviting main menu. Include: game title/logo, play button (prominent), high scores access, settings access. The menu should reflect your game's theme and get players excited to play.

## Task 26: Settings Screen
Create a settings screen with: sound toggle, haptics toggle, maybe a color theme option. Remember settings in AsyncStorage. Keep it simple but functional.

## Task 27: Tutorial or First-Time Experience
Help new players understand your game. This could be: overlay hints, a guided first round, or progressive introduction of mechanics. Don't overwhelm - teach one thing at a time. Let players skip if they want.

## Task 28: Pause Functionality
Allow players to pause mid-game. Pause button should be accessible but not interfere with gameplay. Pause screen: resume button, quit to menu option. Game state should freeze completely when paused.

## Task 29: Level or Wave System
If appropriate for your game, add levels or waves. Each level could introduce: new obstacles, faster speed, new mechanics, or visual changes. Give players a sense of progression beyond just score.

## Task 30: Achievement System
Create 5-10 achievements for players to unlock. Mix easy ones (play 10 games) with hard ones (reach score 10000). Store achievement progress. Show notifications when unlocked. Give players goals beyond high scores.

## Task 31: Statistics Tracking
Track interesting gameplay statistics. Ideas: total games played, total score across all games, highest combo ever, total play time, objects collected/destroyed. Show these somewhere (stats screen or game over).

## Task 32: Daily Challenge Concept
Add a daily challenge or daily reward system. This could be: a special game mode, bonus starting power-up, or streak rewards for playing daily. Gives players a reason to return each day.

## Task 33: Visual Polish Pass - Animations
Review all animations and add polish. Add subtle idle animations to static elements. Ensure all transitions are smooth. Add anticipation before actions and follow-through after. Make everything feel alive.

## Task 34: Visual Polish Pass - Effects
Add ambient visual effects. Ideas: floating particles, subtle background movement, shimmer effects, glow on important elements. Don't distract from gameplay but add atmosphere.

## Task 35: Screen Transitions
Implement smooth transitions between screens. Fade, slide, or creative transitions that match your theme. Avoid jarring instant screen changes. Make navigation feel polished.

## Task 36: Loading and Splash Screen
Create a branded loading/splash screen. Show your game logo or title. Handle asset loading gracefully. Keep it short but memorable.

## Task 37: Performance Optimization
Review and optimize performance. Check for unnecessary re-renders. Ensure animations stay at 60fps. Optimize particle counts if needed. Test on lower-end device assumptions.

## Task 38: Error Handling
Add graceful error handling. Catch and handle storage errors. Handle audio loading failures. Prevent crashes from edge cases. Log errors for debugging.

## Task 39: Responsive Layout
Ensure the game works on different screen sizes. Test layout on small phones and tablets. Adjust scaling if needed. Important elements should never be cut off.

## Task 40: Accessibility Considerations
Add basic accessibility features. Ensure text is readable (good contrast, reasonable size). Make touch targets big enough. Consider adding high contrast mode option.

## Task 41: App Icon Preparation
Create or document app icon requirements. The icon should represent your game's theme. Note: actual icon asset creation may be separate, but prepare the configuration.

## Task 42: Final Menu Polish
Review and polish all menus. Ensure consistent styling. Check button states (normal, pressed). Verify all navigation flows work correctly.

## Task 43: Sound Balance
If sounds are implemented, balance audio levels. Effects shouldn't be jarring. Music (if any) shouldn't overpower effects. Test with headphones and speakers.

## Task 44: Gameplay Balance Pass
Playtest and adjust difficulty curve. Early game should be accessible. Difficulty should ramp fairly. Expert players should be challenged. Find the fun zone.

## Task 45: Bug Hunt
Test all features systematically. Try to break things (rapid tapping, weird timing, etc.). Fix any crashes or glitches found. Ensure game over always triggers correctly.

## Task 46: Code Cleanup
Review code organization. Remove unused code or comments. Ensure consistent naming conventions. Add comments to complex logic. Make code maintainable.

## Task 47: Final Testing Round
Complete playthrough testing. Verify: start to game over flow, all screens accessible, settings persist, high scores save, achievements work.

## Task 48: Documentation
Update or create README.md. Document: how to run the project, game description, any special setup needed. Brief architecture overview for future development.

## Task 49: Build Test
Test the Expo build process. Run expo export or expo build commands. Verify no build errors. Test the built version if possible.

## Task 50: Polish and Ship Prep
Final review of everything. Make any last small improvements. Ensure the game is fun and complete. Prepare for sharing or further development.

---

## Creative Freedom Notes

This task list is intentionally vague on specifics. The AI should make creative decisions about:

- **Game type**: Could be endless runner, timing game, puzzle, reflex test, collection game, avoidance game, etc.
- **Theme**: Space, nature, abstract, cute animals, geometric, retro, underwater, etc.
- **Art style**: Minimal, colorful, neon, pastel, pixel art inspired, etc.
- **Core mechanic**: Tap, swipe, hold, drag, tilt - whatever fits the concept
- **Mood**: Relaxing, intense, whimsical, challenging, zen, chaotic

The goal is a unique, playable, polished casual game that could actually entertain someone for a few minutes at a time.

Good luck, little AI. Make something cool.
