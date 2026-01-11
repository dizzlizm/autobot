# Tower Stack - Mobile Game Tasks

> **Game Concept**: Addictive tower-stacking game where players tap to drop blocks.
> Perfect timing = perfect stack. Mistimed = block gets cut. Stack as high as possible!
>
> **Monetization**: Interstitial ads every 3 games, rewarded video for continues & 2x score
> **Session Length**: 30-90 seconds per round (perfect for ad breaks)
> **Target**: 5-10 daily sessions per user

---

## Task 1: Initialize Expo project with proper structure

Set up the Expo React Native project with all required dependencies.

**Create these files:**

1. **package.json**:
```json
{
  "name": "tower-stack",
  "version": "1.0.0",
  "main": "expo-router/entry",
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "test": "jest",
    "lint": "eslint ."
  },
  "dependencies": {
    "expo": "~50.0.0",
    "expo-router": "~3.4.0",
    "expo-av": "~13.10.0",
    "expo-haptics": "~12.8.0",
    "expo-linear-gradient": "~12.7.0",
    "expo-status-bar": "~1.11.0",
    "react": "18.2.0",
    "react-native": "0.73.0",
    "react-native-reanimated": "~3.6.0",
    "react-native-gesture-handler": "~2.14.0",
    "react-native-safe-area-context": "4.8.2",
    "react-native-screens": "~3.29.0",
    "@react-native-async-storage/async-storage": "1.21.0",
    "react-native-google-mobile-ads": "^13.0.0"
  },
  "devDependencies": {
    "@babel/core": "^7.20.0",
    "@types/react": "~18.2.45",
    "typescript": "^5.3.0",
    "eslint": "^8.0.0"
  }
}
```

2. **app.json**:
```json
{
  "expo": {
    "name": "Tower Stack",
    "slug": "tower-stack",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "userInterfaceStyle": "dark",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "cover",
      "backgroundColor": "#1a1a2e"
    },
    "assetBundlePatterns": ["**/*"],
    "ios": {
      "supportsTablet": false,
      "bundleIdentifier": "com.yourname.towerstack"
    },
    "android": {
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#1a1a2e"
      },
      "package": "com.yourname.towerstack"
    },
    "plugins": [
      "expo-router",
      [
        "react-native-google-mobile-ads",
        {
          "androidAppId": "ca-app-pub-XXXXXXXX~XXXXXXXX",
          "iosAppId": "ca-app-pub-XXXXXXXX~XXXXXXXX"
        }
      ]
    ]
  }
}
```

3. **tsconfig.json**:
```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

4. Create directory structure:
   - `app/` (for expo-router)
   - `components/`
   - `hooks/`
   - `utils/`
   - `constants/`
   - `assets/`

5. **app/_layout.tsx**: Root layout with SafeAreaProvider

6. **app/index.tsx**: Basic placeholder screen with "Tower Stack" text

---

## Task 2: Create game constants and theme system

Create the visual foundation and game balance constants.

**File: constants/theme.ts**
```typescript
export const COLORS = {
  background: '#1a1a2e',
  backgroundGradient: ['#1a1a2e', '#16213e', '#0f3460'],

  // Block colors (cycle through these)
  blocks: [
    '#e94560', // Red
    '#f39c12', // Orange
    '#2ecc71', // Green
    '#3498db', // Blue
    '#9b59b6', // Purple
    '#1abc9c', // Teal
    '#e74c3c', // Coral
    '#f1c40f', // Yellow
  ],

  perfect: '#00ff88',
  ui: {
    text: '#ffffff',
    textSecondary: '#a0a0a0',
    accent: '#e94560',
    button: '#e94560',
    buttonText: '#ffffff',
  }
};

export const GAME = {
  // Canvas
  GAME_WIDTH: 400,
  GAME_HEIGHT: 700,

  // Blocks
  INITIAL_BLOCK_WIDTH: 200,
  BLOCK_HEIGHT: 40,
  MIN_BLOCK_WIDTH: 20,

  // Movement
  INITIAL_SPEED: 3,
  SPEED_INCREMENT: 0.15,
  MAX_SPEED: 12,

  // Scoring
  PERFECT_THRESHOLD: 5, // pixels tolerance for "perfect"
  PERFECT_BONUS: 50,
  BASE_POINTS: 10,

  // Difficulty
  BLOCKS_PER_SPEED_INCREASE: 5,
};

export const ADS = {
  GAMES_BETWEEN_INTERSTITIAL: 3,
  REWARDED_CONTINUE_ENABLED: true,
  REWARDED_DOUBLE_SCORE_ENABLED: true,
};
```

**File: constants/sounds.ts**
```typescript
export const SOUNDS = {
  tap: require('../assets/sounds/tap.mp3'),
  perfect: require('../assets/sounds/perfect.mp3'),
  slice: require('../assets/sounds/slice.mp3'),
  gameOver: require('../assets/sounds/gameover.mp3'),
  newHighScore: require('../assets/sounds/highscore.mp3'),
};
```

Create placeholder files:
- `assets/sounds/` directory (we'll add sounds later)
- `assets/icon.png` (1024x1024 placeholder)
- `assets/splash.png` (1284x2778 placeholder)

---

## Task 3: Build the game engine core - Block class and physics

Create the core game logic for blocks and stacking mechanics.

**File: utils/Block.ts**
```typescript
import { GAME, COLORS } from '@/constants/theme';

export interface BlockState {
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  isMoving: boolean;
  direction: 1 | -1;
  speed: number;
}

export function createBlock(
  stackHeight: number,
  previousBlock: BlockState | null,
  blockIndex: number
): BlockState {
  const width = previousBlock?.width ?? GAME.INITIAL_BLOCK_WIDTH;
  const speed = Math.min(
    GAME.INITIAL_SPEED + Math.floor(blockIndex / GAME.BLOCKS_PER_SPEED_INCREASE) * GAME.SPEED_INCREMENT,
    GAME.MAX_SPEED
  );

  return {
    x: -width, // Start off-screen left
    y: GAME.GAME_HEIGHT - GAME.BLOCK_HEIGHT - (stackHeight * GAME.BLOCK_HEIGHT),
    width,
    height: GAME.BLOCK_HEIGHT,
    color: COLORS.blocks[blockIndex % COLORS.blocks.length],
    isMoving: true,
    direction: 1,
    speed,
  };
}

export function updateBlock(block: BlockState, canvasWidth: number): BlockState {
  if (!block.isMoving) return block;

  let newX = block.x + (block.speed * block.direction);
  let newDirection = block.direction;

  // Bounce off edges
  if (newX + block.width > canvasWidth) {
    newX = canvasWidth - block.width;
    newDirection = -1;
  } else if (newX < 0) {
    newX = 0;
    newDirection = 1;
  }

  return {
    ...block,
    x: newX,
    direction: newDirection,
  };
}

export interface StackResult {
  success: boolean;
  isPerfect: boolean;
  newBlock: BlockState | null;
  slicedOff: number;
  points: number;
}

export function stackBlock(
  movingBlock: BlockState,
  targetBlock: BlockState | null
): StackResult {
  if (!targetBlock) {
    // First block - always succeeds
    return {
      success: true,
      isPerfect: true,
      newBlock: { ...movingBlock, isMoving: false },
      slicedOff: 0,
      points: GAME.BASE_POINTS + GAME.PERFECT_BONUS,
    };
  }

  const overlap = calculateOverlap(movingBlock, targetBlock);

  if (overlap <= 0) {
    // Complete miss
    return {
      success: false,
      isPerfect: false,
      newBlock: null,
      slicedOff: movingBlock.width,
      points: 0,
    };
  }

  const difference = Math.abs(movingBlock.x - targetBlock.x);
  const isPerfect = difference <= GAME.PERFECT_THRESHOLD;

  // Calculate new block position and size
  const newX = Math.max(movingBlock.x, targetBlock.x);
  const newWidth = isPerfect ? movingBlock.width : overlap;

  if (newWidth < GAME.MIN_BLOCK_WIDTH) {
    return {
      success: false,
      isPerfect: false,
      newBlock: null,
      slicedOff: movingBlock.width,
      points: 0,
    };
  }

  const slicedOff = movingBlock.width - newWidth;
  const points = isPerfect
    ? GAME.BASE_POINTS + GAME.PERFECT_BONUS
    : GAME.BASE_POINTS;

  return {
    success: true,
    isPerfect,
    newBlock: {
      ...movingBlock,
      x: newX,
      width: newWidth,
      isMoving: false,
    },
    slicedOff,
    points,
  };
}

function calculateOverlap(block1: BlockState, block2: BlockState): number {
  const left = Math.max(block1.x, block2.x);
  const right = Math.min(block1.x + block1.width, block2.x + block2.width);
  return right - left;
}
```

---

## Task 4: Create the useGameLoop hook with Reanimated

Build the game loop using react-native-reanimated for smooth 60fps animation.

**File: hooks/useGameLoop.ts**
```typescript
import { useCallback, useRef, useState } from 'react';
import { useSharedValue, useAnimatedStyle, withTiming, runOnJS } from 'react-native-reanimated';
import { BlockState, createBlock, updateBlock, stackBlock, StackResult } from '@/utils/Block';
import { GAME } from '@/constants/theme';

export interface GameState {
  blocks: BlockState[];
  currentBlock: BlockState | null;
  score: number;
  perfectStreak: number;
  isPlaying: boolean;
  isGameOver: boolean;
}

export function useGameLoop() {
  const [gameState, setGameState] = useState<GameState>({
    blocks: [],
    currentBlock: null,
    score: 0,
    perfectStreak: 0,
    isPlaying: false,
    isGameOver: false,
  });

  const frameId = useRef<number | null>(null);
  const lastTime = useRef<number>(0);

  const cameraY = useSharedValue(0);

  const startGame = useCallback(() => {
    const firstBlock = createBlock(0, null, 0);
    firstBlock.x = (GAME.GAME_WIDTH - firstBlock.width) / 2;
    firstBlock.isMoving = false;

    const secondBlock = createBlock(1, firstBlock, 1);

    setGameState({
      blocks: [firstBlock],
      currentBlock: secondBlock,
      score: 0,
      perfectStreak: 0,
      isPlaying: true,
      isGameOver: false,
    });

    cameraY.value = 0;
    startLoop();
  }, []);

  const startLoop = useCallback(() => {
    const loop = (time: number) => {
      if (lastTime.current === 0) lastTime.current = time;
      const delta = time - lastTime.current;

      if (delta >= 16) { // ~60fps
        lastTime.current = time;

        setGameState(prev => {
          if (!prev.isPlaying || !prev.currentBlock) return prev;

          const updatedBlock = updateBlock(prev.currentBlock, GAME.GAME_WIDTH);
          return { ...prev, currentBlock: updatedBlock };
        });
      }

      frameId.current = requestAnimationFrame(loop);
    };

    frameId.current = requestAnimationFrame(loop);
  }, []);

  const stopLoop = useCallback(() => {
    if (frameId.current) {
      cancelAnimationFrame(frameId.current);
      frameId.current = null;
    }
    lastTime.current = 0;
  }, []);

  const handleTap = useCallback((): StackResult | null => {
    let result: StackResult | null = null;

    setGameState(prev => {
      if (!prev.isPlaying || !prev.currentBlock) return prev;

      const targetBlock = prev.blocks[prev.blocks.length - 1] || null;
      result = stackBlock(prev.currentBlock, targetBlock);

      if (!result.success) {
        stopLoop();
        return {
          ...prev,
          isPlaying: false,
          isGameOver: true,
          currentBlock: null,
        };
      }

      const newBlocks = [...prev.blocks, result.newBlock!];
      const newStreak = result.isPerfect ? prev.perfectStreak + 1 : 0;
      const streakBonus = result.isPerfect ? newStreak * 5 : 0;

      // Move camera up
      if (newBlocks.length > 8) {
        cameraY.value = withTiming(
          (newBlocks.length - 8) * GAME.BLOCK_HEIGHT,
          { duration: 200 }
        );
      }

      const nextBlock = createBlock(newBlocks.length, result.newBlock!, newBlocks.length);

      return {
        ...prev,
        blocks: newBlocks,
        currentBlock: nextBlock,
        score: prev.score + result.points + streakBonus,
        perfectStreak: newStreak,
      };
    });

    return result;
  }, [stopLoop]);

  const resetGame = useCallback(() => {
    stopLoop();
    setGameState({
      blocks: [],
      currentBlock: null,
      score: 0,
      perfectStreak: 0,
      isPlaying: false,
      isGameOver: false,
    });
    cameraY.value = 0;
  }, [stopLoop]);

  const cameraStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: cameraY.value }],
  }));

  return {
    gameState,
    startGame,
    handleTap,
    resetGame,
    cameraStyle,
  };
}
```

---

## Task 5: Build the GameCanvas component with block rendering

Create the main game view that renders all blocks.

**File: components/GameCanvas.tsx**
```typescript
import React from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import Animated from 'react-native-reanimated';
import { BlockState } from '@/utils/Block';
import { COLORS, GAME } from '@/constants/theme';

interface Props {
  blocks: BlockState[];
  currentBlock: BlockState | null;
  cameraStyle: any;
}

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const SCALE = SCREEN_WIDTH / GAME.GAME_WIDTH;

export function GameCanvas({ blocks, currentBlock, cameraStyle }: Props) {
  return (
    <View style={styles.container}>
      <Animated.View style={[styles.canvas, cameraStyle]}>
        {/* Render stacked blocks */}
        {blocks.map((block, index) => (
          <Block key={index} block={block} />
        ))}

        {/* Render moving block */}
        {currentBlock && <Block block={currentBlock} isActive />}
      </Animated.View>
    </View>
  );
}

interface BlockProps {
  block: BlockState;
  isActive?: boolean;
}

function Block({ block, isActive }: BlockProps) {
  return (
    <View
      style={[
        styles.block,
        {
          left: block.x * SCALE,
          bottom: (GAME.GAME_HEIGHT - block.y - block.height) * SCALE,
          width: block.width * SCALE,
          height: block.height * SCALE,
          backgroundColor: block.color,
        },
        isActive && styles.activeBlock,
      ]}
    />
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: COLORS.background,
  },
  canvas: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: GAME.GAME_HEIGHT * SCALE,
  },
  block: {
    position: 'absolute',
    borderRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 5,
  },
  activeBlock: {
    shadowOpacity: 0.5,
    shadowRadius: 8,
  },
});
```

---

## Task 6: Create the HUD (score, streak, high score display)

Build the heads-up display showing game stats.

**File: components/HUD.tsx**
```typescript
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '@/constants/theme';

interface Props {
  score: number;
  highScore: number;
  perfectStreak: number;
  blocksStacked: number;
}

export function HUD({ score, highScore, perfectStreak, blocksStacked }: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <View style={styles.stat}>
          <Text style={styles.label}>SCORE</Text>
          <Text style={styles.value}>{score.toLocaleString()}</Text>
        </View>

        <View style={styles.stat}>
          <Text style={styles.label}>BEST</Text>
          <Text style={styles.valueBest}>{highScore.toLocaleString()}</Text>
        </View>
      </View>

      {perfectStreak > 1 && (
        <View style={styles.streakContainer}>
          <Text style={styles.streakText}>
            🔥 PERFECT x{perfectStreak}
          </Text>
        </View>
      )}

      <View style={styles.heightIndicator}>
        <Text style={styles.heightText}>{blocksStacked}m</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 60,
    left: 0,
    right: 0,
    paddingHorizontal: 20,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  stat: {
    alignItems: 'center',
  },
  label: {
    fontSize: 12,
    color: COLORS.ui.textSecondary,
    fontWeight: '600',
    letterSpacing: 1,
  },
  value: {
    fontSize: 36,
    color: COLORS.ui.text,
    fontWeight: 'bold',
  },
  valueBest: {
    fontSize: 36,
    color: COLORS.ui.accent,
    fontWeight: 'bold',
  },
  streakContainer: {
    alignItems: 'center',
    marginTop: 10,
  },
  streakText: {
    fontSize: 24,
    color: COLORS.perfect,
    fontWeight: 'bold',
  },
  heightIndicator: {
    position: 'absolute',
    right: 20,
    top: 80,
  },
  heightText: {
    fontSize: 18,
    color: COLORS.ui.textSecondary,
  },
});
```

---

## Task 7: Create the GameOverModal with continue and replay options

Build the game over screen with ad-enabled continue.

**File: components/GameOverModal.tsx**
```typescript
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Modal } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { COLORS } from '@/constants/theme';

interface Props {
  visible: boolean;
  score: number;
  highScore: number;
  isNewHighScore: boolean;
  blocksStacked: number;
  onReplay: () => void;
  onContinue: () => void; // Watch ad to continue
  onDoubleScore: () => void; // Watch ad for 2x score
  canContinue: boolean;
}

export function GameOverModal({
  visible,
  score,
  highScore,
  isNewHighScore,
  blocksStacked,
  onReplay,
  onContinue,
  onDoubleScore,
  canContinue,
}: Props) {
  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={styles.modal}>
          {isNewHighScore && (
            <Text style={styles.newHighScore}>🏆 NEW HIGH SCORE!</Text>
          )}

          <Text style={styles.gameOver}>GAME OVER</Text>

          <View style={styles.stats}>
            <View style={styles.statRow}>
              <Text style={styles.statLabel}>Score</Text>
              <Text style={styles.statValue}>{score.toLocaleString()}</Text>
            </View>
            <View style={styles.statRow}>
              <Text style={styles.statLabel}>Height</Text>
              <Text style={styles.statValue}>{blocksStacked}m</Text>
            </View>
            <View style={styles.statRow}>
              <Text style={styles.statLabel}>Best</Text>
              <Text style={styles.statValueBest}>{highScore.toLocaleString()}</Text>
            </View>
          </View>

          {canContinue && (
            <TouchableOpacity style={styles.continueButton} onPress={onContinue}>
              <LinearGradient
                colors={['#2ecc71', '#27ae60']}
                style={styles.buttonGradient}
              >
                <Text style={styles.buttonIcon}>▶️</Text>
                <Text style={styles.buttonText}>Continue</Text>
                <Text style={styles.adLabel}>Watch Ad</Text>
              </LinearGradient>
            </TouchableOpacity>
          )}

          <TouchableOpacity style={styles.doubleButton} onPress={onDoubleScore}>
            <LinearGradient
              colors={['#f39c12', '#e67e22']}
              style={styles.buttonGradient}
            >
              <Text style={styles.buttonIcon}>2️⃣</Text>
              <Text style={styles.buttonText}>Double Score</Text>
              <Text style={styles.adLabel}>Watch Ad</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity style={styles.replayButton} onPress={onReplay}>
            <Text style={styles.replayText}>🔄 Play Again</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modal: {
    backgroundColor: COLORS.background,
    borderRadius: 20,
    padding: 30,
    width: '85%',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: COLORS.ui.accent,
  },
  newHighScore: {
    fontSize: 20,
    color: COLORS.perfect,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  gameOver: {
    fontSize: 32,
    color: COLORS.ui.text,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  stats: {
    width: '100%',
    marginBottom: 25,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 5,
  },
  statLabel: {
    fontSize: 18,
    color: COLORS.ui.textSecondary,
  },
  statValue: {
    fontSize: 18,
    color: COLORS.ui.text,
    fontWeight: 'bold',
  },
  statValueBest: {
    fontSize: 18,
    color: COLORS.ui.accent,
    fontWeight: 'bold',
  },
  continueButton: {
    width: '100%',
    marginBottom: 10,
    borderRadius: 12,
    overflow: 'hidden',
  },
  doubleButton: {
    width: '100%',
    marginBottom: 15,
    borderRadius: 12,
    overflow: 'hidden',
  },
  buttonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    paddingHorizontal: 20,
  },
  buttonIcon: {
    fontSize: 20,
    marginRight: 10,
  },
  buttonText: {
    fontSize: 18,
    color: '#fff',
    fontWeight: 'bold',
  },
  adLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
    marginLeft: 10,
  },
  replayButton: {
    paddingVertical: 15,
  },
  replayText: {
    fontSize: 18,
    color: COLORS.ui.textSecondary,
  },
});
```

---

## Task 8: Create sound and haptic feedback system

Build the audio/haptic manager for immersive feedback.

**File: hooks/useSound.ts**
```typescript
import { useEffect, useRef, useCallback } from 'react';
import { Audio } from 'expo-av';
import * as Haptics from 'expo-haptics';

interface SoundEffects {
  tap: Audio.Sound | null;
  perfect: Audio.Sound | null;
  slice: Audio.Sound | null;
  gameOver: Audio.Sound | null;
  highScore: Audio.Sound | null;
}

export function useSound() {
  const sounds = useRef<SoundEffects>({
    tap: null,
    perfect: null,
    slice: null,
    gameOver: null,
    highScore: null,
  });

  const isMuted = useRef(false);

  useEffect(() => {
    loadSounds();
    return () => unloadSounds();
  }, []);

  const loadSounds = async () => {
    try {
      await Audio.setAudioModeAsync({
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });

      // Load sound files - create simple placeholder sounds for now
      // In production, replace with actual sound files
      const soundFiles = {
        tap: require('../assets/sounds/tap.mp3'),
        perfect: require('../assets/sounds/perfect.mp3'),
        slice: require('../assets/sounds/slice.mp3'),
        gameOver: require('../assets/sounds/gameover.mp3'),
        highScore: require('../assets/sounds/highscore.mp3'),
      };

      for (const [key, file] of Object.entries(soundFiles)) {
        try {
          const { sound } = await Audio.Sound.createAsync(file);
          sounds.current[key as keyof SoundEffects] = sound;
        } catch (e) {
          console.log(`Could not load sound: ${key}`);
        }
      }
    } catch (error) {
      console.log('Error loading sounds:', error);
    }
  };

  const unloadSounds = async () => {
    for (const sound of Object.values(sounds.current)) {
      if (sound) {
        await sound.unloadAsync();
      }
    }
  };

  const playSound = useCallback(async (name: keyof SoundEffects) => {
    if (isMuted.current) return;

    const sound = sounds.current[name];
    if (sound) {
      try {
        await sound.replayAsync();
      } catch (e) {
        // Ignore playback errors
      }
    }
  }, []);

  const playTap = useCallback(() => {
    playSound('tap');
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  }, [playSound]);

  const playPerfect = useCallback(() => {
    playSound('perfect');
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  }, [playSound]);

  const playSlice = useCallback(() => {
    playSound('slice');
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  }, [playSound]);

  const playGameOver = useCallback(() => {
    playSound('gameOver');
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
  }, [playSound]);

  const playHighScore = useCallback(() => {
    playSound('highScore');
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  }, [playSound]);

  const toggleMute = useCallback(() => {
    isMuted.current = !isMuted.current;
    return isMuted.current;
  }, []);

  return {
    playTap,
    playPerfect,
    playSlice,
    playGameOver,
    playHighScore,
    toggleMute,
  };
}
```

Create placeholder sound files:
- `assets/sounds/tap.mp3`
- `assets/sounds/perfect.mp3`
- `assets/sounds/slice.mp3`
- `assets/sounds/gameover.mp3`
- `assets/sounds/highscore.mp3`

(These can be empty MP3 files for now - real sounds added later)

---

## Task 9: Create persistent storage for high scores and settings

Build AsyncStorage wrapper for game data persistence.

**File: hooks/useStorage.ts**
```typescript
import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  HIGH_SCORE: '@tower_stack_high_score',
  GAMES_PLAYED: '@tower_stack_games_played',
  TOTAL_BLOCKS: '@tower_stack_total_blocks',
  SETTINGS: '@tower_stack_settings',
  GAMES_SINCE_AD: '@tower_stack_games_since_ad',
};

interface Settings {
  soundEnabled: boolean;
  hapticEnabled: boolean;
}

interface GameStats {
  highScore: number;
  gamesPlayed: number;
  totalBlocks: number;
}

const DEFAULT_SETTINGS: Settings = {
  soundEnabled: true,
  hapticEnabled: true,
};

export function useStorage() {
  const [stats, setStats] = useState<GameStats>({
    highScore: 0,
    gamesPlayed: 0,
    totalBlocks: 0,
  });

  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [gamesSinceAd, setGamesSinceAd] = useState(0);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [highScore, gamesPlayed, totalBlocks, savedSettings, adCount] = await Promise.all([
        AsyncStorage.getItem(KEYS.HIGH_SCORE),
        AsyncStorage.getItem(KEYS.GAMES_PLAYED),
        AsyncStorage.getItem(KEYS.TOTAL_BLOCKS),
        AsyncStorage.getItem(KEYS.SETTINGS),
        AsyncStorage.getItem(KEYS.GAMES_SINCE_AD),
      ]);

      setStats({
        highScore: highScore ? parseInt(highScore, 10) : 0,
        gamesPlayed: gamesPlayed ? parseInt(gamesPlayed, 10) : 0,
        totalBlocks: totalBlocks ? parseInt(totalBlocks, 10) : 0,
      });

      if (savedSettings) {
        setSettings(JSON.parse(savedSettings));
      }

      setGamesSinceAd(adCount ? parseInt(adCount, 10) : 0);
      setIsLoaded(true);
    } catch (error) {
      console.error('Error loading data:', error);
      setIsLoaded(true);
    }
  };

  const updateHighScore = useCallback(async (score: number) => {
    if (score > stats.highScore) {
      await AsyncStorage.setItem(KEYS.HIGH_SCORE, score.toString());
      setStats(prev => ({ ...prev, highScore: score }));
      return true; // New high score
    }
    return false;
  }, [stats.highScore]);

  const recordGame = useCallback(async (blocksStacked: number) => {
    const newGamesPlayed = stats.gamesPlayed + 1;
    const newTotalBlocks = stats.totalBlocks + blocksStacked;
    const newGamesSinceAd = gamesSinceAd + 1;

    await Promise.all([
      AsyncStorage.setItem(KEYS.GAMES_PLAYED, newGamesPlayed.toString()),
      AsyncStorage.setItem(KEYS.TOTAL_BLOCKS, newTotalBlocks.toString()),
      AsyncStorage.setItem(KEYS.GAMES_SINCE_AD, newGamesSinceAd.toString()),
    ]);

    setStats(prev => ({
      ...prev,
      gamesPlayed: newGamesPlayed,
      totalBlocks: newTotalBlocks,
    }));
    setGamesSinceAd(newGamesSinceAd);
  }, [stats, gamesSinceAd]);

  const resetAdCounter = useCallback(async () => {
    await AsyncStorage.setItem(KEYS.GAMES_SINCE_AD, '0');
    setGamesSinceAd(0);
  }, []);

  const updateSettings = useCallback(async (newSettings: Partial<Settings>) => {
    const updated = { ...settings, ...newSettings };
    await AsyncStorage.setItem(KEYS.SETTINGS, JSON.stringify(updated));
    setSettings(updated);
  }, [settings]);

  return {
    stats,
    settings,
    gamesSinceAd,
    isLoaded,
    updateHighScore,
    recordGame,
    resetAdCounter,
    updateSettings,
  };
}
```

---

## Task 10: Implement AdMob integration

Create the ad management system with interstitials and rewarded videos.

**File: hooks/useAds.ts**
```typescript
import { useEffect, useRef, useCallback, useState } from 'react';
import {
  InterstitialAd,
  RewardedAd,
  AdEventType,
  RewardedAdEventType,
  TestIds,
} from 'react-native-google-mobile-ads';
import { ADS } from '@/constants/theme';

// Use test IDs during development
const INTERSTITIAL_ID = __DEV__
  ? TestIds.INTERSTITIAL
  : 'ca-app-pub-XXXXX/XXXXX'; // Replace with real ID

const REWARDED_ID = __DEV__
  ? TestIds.REWARDED
  : 'ca-app-pub-XXXXX/XXXXX'; // Replace with real ID

export function useAds() {
  const interstitial = useRef<InterstitialAd | null>(null);
  const rewarded = useRef<RewardedAd | null>(null);

  const [interstitialLoaded, setInterstitialLoaded] = useState(false);
  const [rewardedLoaded, setRewardedLoaded] = useState(false);

  const rewardCallback = useRef<(() => void) | null>(null);

  useEffect(() => {
    loadInterstitial();
    loadRewarded();

    return () => {
      // Cleanup
    };
  }, []);

  const loadInterstitial = useCallback(() => {
    setInterstitialLoaded(false);

    interstitial.current = InterstitialAd.createForAdRequest(INTERSTITIAL_ID, {
      requestNonPersonalizedAdsOnly: true,
    });

    const unsubscribeLoaded = interstitial.current.addAdEventListener(
      AdEventType.LOADED,
      () => setInterstitialLoaded(true)
    );

    const unsubscribeClosed = interstitial.current.addAdEventListener(
      AdEventType.CLOSED,
      () => {
        loadInterstitial(); // Preload next
      }
    );

    interstitial.current.load();

    return () => {
      unsubscribeLoaded();
      unsubscribeClosed();
    };
  }, []);

  const loadRewarded = useCallback(() => {
    setRewardedLoaded(false);

    rewarded.current = RewardedAd.createForAdRequest(REWARDED_ID, {
      requestNonPersonalizedAdsOnly: true,
    });

    const unsubscribeLoaded = rewarded.current.addAdEventListener(
      RewardedAdEventType.LOADED,
      () => setRewardedLoaded(true)
    );

    const unsubscribeEarned = rewarded.current.addAdEventListener(
      RewardedAdEventType.EARNED_REWARD,
      () => {
        if (rewardCallback.current) {
          rewardCallback.current();
          rewardCallback.current = null;
        }
      }
    );

    const unsubscribeClosed = rewarded.current.addAdEventListener(
      AdEventType.CLOSED,
      () => {
        loadRewarded(); // Preload next
      }
    );

    rewarded.current.load();

    return () => {
      unsubscribeLoaded();
      unsubscribeEarned();
      unsubscribeClosed();
    };
  }, []);

  const showInterstitial = useCallback(async () => {
    if (interstitialLoaded && interstitial.current) {
      await interstitial.current.show();
      return true;
    }
    return false;
  }, [interstitialLoaded]);

  const showRewarded = useCallback(async (onReward: () => void) => {
    if (rewardedLoaded && rewarded.current) {
      rewardCallback.current = onReward;
      await rewarded.current.show();
      return true;
    }
    return false;
  }, [rewardedLoaded]);

  return {
    interstitialLoaded,
    rewardedLoaded,
    showInterstitial,
    showRewarded,
  };
}
```

---

## Task 11: Build the main game screen integrating all components

Assemble all pieces into the main playable game screen.

**File: app/index.tsx**
```typescript
import React, { useCallback, useEffect, useState } from 'react';
import { View, StyleSheet, TouchableWithoutFeedback, Text } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

import { GameCanvas } from '@/components/GameCanvas';
import { HUD } from '@/components/HUD';
import { GameOverModal } from '@/components/GameOverModal';
import { useGameLoop } from '@/hooks/useGameLoop';
import { useSound } from '@/hooks/useSound';
import { useStorage } from '@/hooks/useStorage';
import { useAds } from '@/hooks/useAds';
import { COLORS, ADS } from '@/constants/theme';

export default function GameScreen() {
  const { gameState, startGame, handleTap, resetGame, cameraStyle } = useGameLoop();
  const { playTap, playPerfect, playSlice, playGameOver, playHighScore } = useSound();
  const { stats, gamesSinceAd, updateHighScore, recordGame, resetAdCounter } = useStorage();
  const { showInterstitial, showRewarded, rewardedLoaded } = useAds();

  const [showGameOver, setShowGameOver] = useState(false);
  const [isNewHighScore, setIsNewHighScore] = useState(false);
  const [canContinue, setCanContinue] = useState(true);

  // Handle tap during gameplay
  const onTap = useCallback(() => {
    if (!gameState.isPlaying && !gameState.isGameOver) {
      // Start new game
      startGame();
      return;
    }

    if (gameState.isPlaying) {
      const result = handleTap();

      if (result) {
        if (result.success) {
          if (result.isPerfect) {
            playPerfect();
          } else {
            playTap();
          }
        } else {
          playGameOver();
        }
      }
    }
  }, [gameState.isPlaying, gameState.isGameOver, startGame, handleTap, playTap, playPerfect, playGameOver]);

  // Handle game over
  useEffect(() => {
    if (gameState.isGameOver && !showGameOver) {
      handleGameEnd();
    }
  }, [gameState.isGameOver]);

  const handleGameEnd = async () => {
    const isNew = await updateHighScore(gameState.score);
    setIsNewHighScore(isNew);

    if (isNew) {
      playHighScore();
    }

    await recordGame(gameState.blocks.length);

    // Show interstitial every N games
    if (gamesSinceAd >= ADS.GAMES_BETWEEN_INTERSTITIAL) {
      await showInterstitial();
      await resetAdCounter();
    }

    setShowGameOver(true);
    setCanContinue(true);
  };

  const handleReplay = useCallback(() => {
    setShowGameOver(false);
    setIsNewHighScore(false);
    resetGame();
  }, [resetGame]);

  const handleContinue = useCallback(async () => {
    const shown = await showRewarded(() => {
      setShowGameOver(false);
      setCanContinue(false);
      // Resume game from current state
      startGame(); // TODO: Implement proper continue logic
    });

    if (!shown) {
      console.log('Rewarded ad not ready');
    }
  }, [showRewarded, startGame]);

  const handleDoubleScore = useCallback(async () => {
    await showRewarded(() => {
      // Double the final score
      const doubledScore = gameState.score * 2;
      updateHighScore(doubledScore);
      setShowGameOver(false);
      resetGame();
    });
  }, [showRewarded, gameState.score, updateHighScore, resetGame]);

  return (
    <View style={styles.container}>
      <StatusBar style="light" />

      <LinearGradient
        colors={COLORS.backgroundGradient}
        style={StyleSheet.absoluteFill}
      />

      <TouchableWithoutFeedback onPress={onTap}>
        <View style={styles.gameArea}>
          <GameCanvas
            blocks={gameState.blocks}
            currentBlock={gameState.currentBlock}
            cameraStyle={cameraStyle}
          />

          <SafeAreaView style={styles.overlay} edges={['top']}>
            <HUD
              score={gameState.score}
              highScore={stats.highScore}
              perfectStreak={gameState.perfectStreak}
              blocksStacked={gameState.blocks.length}
            />
          </SafeAreaView>

          {!gameState.isPlaying && !gameState.isGameOver && (
            <View style={styles.startPrompt}>
              <Text style={styles.title}>TOWER STACK</Text>
              <Text style={styles.tapToStart}>Tap to Start</Text>
            </View>
          )}
        </View>
      </TouchableWithoutFeedback>

      <GameOverModal
        visible={showGameOver}
        score={gameState.score}
        highScore={stats.highScore}
        isNewHighScore={isNewHighScore}
        blocksStacked={gameState.blocks.length}
        onReplay={handleReplay}
        onContinue={handleContinue}
        onDoubleScore={handleDoubleScore}
        canContinue={canContinue && rewardedLoaded}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  gameArea: {
    flex: 1,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
  },
  startPrompt: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 48,
    fontWeight: 'bold',
    color: COLORS.ui.text,
    marginBottom: 20,
    textShadowColor: COLORS.ui.accent,
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 20,
  },
  tapToStart: {
    fontSize: 20,
    color: COLORS.ui.textSecondary,
  },
});
```

---

## Task 12: Add visual polish - perfect stack effects and animations

Enhance visual feedback with particle effects and animations.

**File: components/PerfectEffect.tsx**
```typescript
import React, { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSequence,
  withDelay,
  runOnJS,
} from 'react-native-reanimated';
import { COLORS } from '@/constants/theme';

interface Props {
  visible: boolean;
  x: number;
  y: number;
  onComplete: () => void;
}

export function PerfectEffect({ visible, x, y, onComplete }: Props) {
  const scale = useSharedValue(0);
  const opacity = useSharedValue(0);
  const translateY = useSharedValue(0);

  useEffect(() => {
    if (visible) {
      scale.value = 0;
      opacity.value = 1;
      translateY.value = 0;

      scale.value = withSequence(
        withTiming(1.5, { duration: 150 }),
        withTiming(1, { duration: 100 })
      );

      translateY.value = withTiming(-50, { duration: 500 });

      opacity.value = withDelay(
        300,
        withTiming(0, { duration: 200 }, () => {
          runOnJS(onComplete)();
        })
      );
    }
  }, [visible]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: scale.value },
      { translateY: translateY.value },
    ],
    opacity: opacity.value,
  }));

  if (!visible) return null;

  return (
    <Animated.View
      style={[
        styles.container,
        { left: x - 50, top: y - 20 },
        animatedStyle,
      ]}
    >
      <Animated.Text style={styles.text}>PERFECT!</Animated.Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    width: 100,
    alignItems: 'center',
  },
  text: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.perfect,
    textShadowColor: COLORS.perfect,
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
});
```

**File: components/SliceEffect.tsx**
```typescript
import React, { useEffect } from 'react';
import { StyleSheet, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSpring,
  Easing,
} from 'react-native-reanimated';
import { GAME } from '@/constants/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const SCALE = SCREEN_WIDTH / GAME.GAME_WIDTH;

interface Props {
  visible: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  direction: 'left' | 'right';
  onComplete: () => void;
}

export function SliceEffect({
  visible, x, y, width, height, color, direction, onComplete
}: Props) {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const rotate = useSharedValue(0);
  const opacity = useSharedValue(1);

  useEffect(() => {
    if (visible) {
      translateX.value = 0;
      translateY.value = 0;
      rotate.value = 0;
      opacity.value = 1;

      const xDirection = direction === 'left' ? -1 : 1;

      translateX.value = withTiming(xDirection * 200, {
        duration: 500,
        easing: Easing.out(Easing.quad),
      });

      translateY.value = withTiming(300, {
        duration: 500,
        easing: Easing.in(Easing.quad),
      });

      rotate.value = withTiming(xDirection * 45, { duration: 500 });

      opacity.value = withTiming(0, { duration: 500 }, () => {
        // onComplete called after animation
      });
    }
  }, [visible, direction]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { rotate: `${rotate.value}deg` },
    ],
    opacity: opacity.value,
  }));

  if (!visible) return null;

  return (
    <Animated.View
      style={[
        styles.slice,
        {
          left: x * SCALE,
          bottom: (GAME.GAME_HEIGHT - y - height) * SCALE,
          width: width * SCALE,
          height: height * SCALE,
          backgroundColor: color,
        },
        animatedStyle,
      ]}
    />
  );
}

const styles = StyleSheet.create({
  slice: {
    position: 'absolute',
    borderRadius: 4,
  },
});
```

---

## Task 13: Create settings screen with sound/haptic toggles

Add a settings overlay for user preferences.

**File: components/SettingsModal.tsx**
```typescript
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Modal, Switch } from 'react-native';
import { COLORS } from '@/constants/theme';

interface Props {
  visible: boolean;
  soundEnabled: boolean;
  hapticEnabled: boolean;
  onSoundToggle: (value: boolean) => void;
  onHapticToggle: (value: boolean) => void;
  onClose: () => void;
  stats: {
    gamesPlayed: number;
    totalBlocks: number;
    highScore: number;
  };
}

export function SettingsModal({
  visible,
  soundEnabled,
  hapticEnabled,
  onSoundToggle,
  onHapticToggle,
  onClose,
  stats,
}: Props) {
  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.modal}>
          <Text style={styles.title}>Settings</Text>

          <View style={styles.section}>
            <View style={styles.row}>
              <Text style={styles.label}>🔊 Sound</Text>
              <Switch
                value={soundEnabled}
                onValueChange={onSoundToggle}
                trackColor={{ false: '#333', true: COLORS.ui.accent }}
                thumbColor="#fff"
              />
            </View>

            <View style={styles.row}>
              <Text style={styles.label}>📳 Haptics</Text>
              <Switch
                value={hapticEnabled}
                onValueChange={onHapticToggle}
                trackColor={{ false: '#333', true: COLORS.ui.accent }}
                thumbColor="#fff"
              />
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Statistics</Text>
            <View style={styles.statRow}>
              <Text style={styles.statLabel}>Games Played</Text>
              <Text style={styles.statValue}>{stats.gamesPlayed}</Text>
            </View>
            <View style={styles.statRow}>
              <Text style={styles.statLabel}>Total Blocks</Text>
              <Text style={styles.statValue}>{stats.totalBlocks}</Text>
            </View>
            <View style={styles.statRow}>
              <Text style={styles.statLabel}>Best Score</Text>
              <Text style={styles.statValue}>{stats.highScore}</Text>
            </View>
          </View>

          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Text style={styles.closeText}>Done</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'flex-end',
  },
  modal: {
    backgroundColor: COLORS.background,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 25,
    paddingBottom: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.ui.text,
    textAlign: 'center',
    marginBottom: 25,
  },
  section: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 16,
    color: COLORS.ui.textSecondary,
    marginBottom: 15,
    fontWeight: '600',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  label: {
    fontSize: 18,
    color: COLORS.ui.text,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  statLabel: {
    fontSize: 16,
    color: COLORS.ui.textSecondary,
  },
  statValue: {
    fontSize: 16,
    color: COLORS.ui.text,
    fontWeight: 'bold',
  },
  closeButton: {
    backgroundColor: COLORS.ui.accent,
    paddingVertical: 15,
    borderRadius: 12,
    alignItems: 'center',
  },
  closeText: {
    fontSize: 18,
    color: '#fff',
    fontWeight: 'bold',
  },
});
```

---

## Task 14: Add tutorial overlay for first-time players

Create an onboarding experience for new users.

**File: components/Tutorial.tsx**
```typescript
import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import { COLORS } from '@/constants/theme';

const { width, height } = Dimensions.get('window');

interface Props {
  visible: boolean;
  onComplete: () => void;
}

export function Tutorial({ visible, onComplete }: Props) {
  const [step, setStep] = useState(0);

  const tapScale = useSharedValue(1);

  React.useEffect(() => {
    tapScale.value = withRepeat(
      withSequence(
        withTiming(1.2, { duration: 500 }),
        withTiming(1, { duration: 500 })
      ),
      -1,
      true
    );
  }, []);

  const tapStyle = useAnimatedStyle(() => ({
    transform: [{ scale: tapScale.value }],
  }));

  const steps = [
    {
      title: 'Welcome to Tower Stack!',
      text: 'Stack blocks as high as you can',
      icon: '🏗️',
    },
    {
      title: 'Tap to Drop',
      text: 'Tap anywhere to drop the moving block',
      icon: '👆',
    },
    {
      title: 'Perfect Timing',
      text: 'Align blocks perfectly for bonus points!',
      icon: '✨',
    },
    {
      title: 'Watch Out!',
      text: 'Misaligned blocks get smaller. Miss completely and it\'s game over!',
      icon: '⚠️',
    },
  ];

  if (!visible) return null;

  const currentStep = steps[step];

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      onComplete();
    }
  };

  return (
    <View style={styles.overlay}>
      <View style={styles.content}>
        <Text style={styles.icon}>{currentStep.icon}</Text>
        <Text style={styles.title}>{currentStep.title}</Text>
        <Text style={styles.text}>{currentStep.text}</Text>

        {step === 1 && (
          <Animated.View style={[styles.tapHint, tapStyle]}>
            <Text style={styles.tapText}>👆</Text>
          </Animated.View>
        )}

        <View style={styles.dots}>
          {steps.map((_, i) => (
            <View
              key={i}
              style={[styles.dot, i === step && styles.dotActive]}
            />
          ))}
        </View>

        <TouchableOpacity style={styles.button} onPress={handleNext}>
          <Text style={styles.buttonText}>
            {step < steps.length - 1 ? 'Next' : 'Let\'s Play!'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  icon: {
    fontSize: 60,
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: COLORS.ui.text,
    marginBottom: 15,
    textAlign: 'center',
  },
  text: {
    fontSize: 18,
    color: COLORS.ui.textSecondary,
    textAlign: 'center',
    lineHeight: 26,
  },
  tapHint: {
    marginTop: 30,
  },
  tapText: {
    fontSize: 50,
  },
  dots: {
    flexDirection: 'row',
    marginTop: 40,
    marginBottom: 30,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.3)',
    marginHorizontal: 5,
  },
  dotActive: {
    backgroundColor: COLORS.ui.accent,
    width: 20,
  },
  button: {
    backgroundColor: COLORS.ui.accent,
    paddingVertical: 15,
    paddingHorizontal: 50,
    borderRadius: 30,
  },
  buttonText: {
    fontSize: 18,
    color: '#fff',
    fontWeight: 'bold',
  },
});
```

---

## Task 15: Implement daily challenge and streak system

Add engagement mechanics with daily challenges.

**File: hooks/useDailyChallenge.ts**
```typescript
import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  LAST_PLAY_DATE: '@tower_daily_last_play',
  CURRENT_STREAK: '@tower_daily_streak',
  DAILY_HIGH: '@tower_daily_high',
};

interface DailyState {
  streak: number;
  todayHighScore: number;
  isNewDay: boolean;
  challengeTarget: number;
  challengeCompleted: boolean;
}

export function useDailyChallenge() {
  const [daily, setDaily] = useState<DailyState>({
    streak: 0,
    todayHighScore: 0,
    isNewDay: false,
    challengeTarget: 0,
    challengeCompleted: false,
  });

  useEffect(() => {
    checkDailyStatus();
  }, []);

  const checkDailyStatus = async () => {
    const today = new Date().toDateString();
    const lastPlay = await AsyncStorage.getItem(KEYS.LAST_PLAY_DATE);
    const streak = await AsyncStorage.getItem(KEYS.CURRENT_STREAK);
    const dailyHigh = await AsyncStorage.getItem(KEYS.DAILY_HIGH);

    let currentStreak = streak ? parseInt(streak, 10) : 0;
    let isNewDay = false;
    let todayHighScore = 0;

    if (lastPlay !== today) {
      isNewDay = true;

      // Check if streak continues (played yesterday)
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      if (lastPlay === yesterday.toDateString()) {
        currentStreak += 1;
      } else if (lastPlay !== today) {
        currentStreak = 1; // Reset streak
      }

      await AsyncStorage.setItem(KEYS.LAST_PLAY_DATE, today);
      await AsyncStorage.setItem(KEYS.CURRENT_STREAK, currentStreak.toString());
      await AsyncStorage.setItem(KEYS.DAILY_HIGH, '0');
    } else {
      todayHighScore = dailyHigh ? parseInt(dailyHigh, 10) : 0;
    }

    // Challenge target scales with streak
    const challengeTarget = 500 + (currentStreak * 100);

    setDaily({
      streak: currentStreak,
      todayHighScore,
      isNewDay,
      challengeTarget,
      challengeCompleted: todayHighScore >= challengeTarget,
    });
  };

  const recordDailyScore = useCallback(async (score: number) => {
    if (score > daily.todayHighScore) {
      await AsyncStorage.setItem(KEYS.DAILY_HIGH, score.toString());

      const newCompleted = score >= daily.challengeTarget;

      setDaily(prev => ({
        ...prev,
        todayHighScore: score,
        challengeCompleted: newCompleted,
      }));

      return newCompleted && !daily.challengeCompleted; // Returns true if just completed
    }
    return false;
  }, [daily]);

  return {
    daily,
    recordDailyScore,
  };
}
```

---

## Task 16: Add app icons and splash screen

Create proper app assets for a polished look.

1. Create `assets/icon.png` (1024x1024):
   - Dark blue gradient background (#1a1a2e to #0f3460)
   - Stack of 4 colorful blocks in center
   - Slight 3D shadow effect
   - Rounded corners will be applied by the system

2. Create `assets/adaptive-icon.png` (1024x1024):
   - Same as icon but with more padding for Android adaptive icons
   - Content should be in center 66% of image

3. Create `assets/splash.png` (1284x2778):
   - Same gradient background
   - "TOWER STACK" text in center
   - Small stack of blocks below text
   - Subtle animated feel (blocks slightly offset)

4. Update `app.json` splash configuration:
```json
{
  "splash": {
    "image": "./assets/splash.png",
    "resizeMode": "cover",
    "backgroundColor": "#1a1a2e"
  }
}
```

---

## Task 17: Performance optimization and testing

Optimize the game for smooth performance on all devices.

**File: utils/performance.ts**
```typescript
import { Platform } from 'react-native';

// Reduce render cycles
export const FRAME_RATE = Platform.OS === 'android' ? 30 : 60;
export const FRAME_TIME = 1000 / FRAME_RATE;

// Object pooling for blocks
class BlockPool {
  private pool: any[] = [];
  private maxSize = 50;

  acquire() {
    return this.pool.pop() || {};
  }

  release(obj: any) {
    if (this.pool.length < this.maxSize) {
      // Reset object
      Object.keys(obj).forEach(key => delete obj[key]);
      this.pool.push(obj);
    }
  }
}

export const blockPool = new BlockPool();

// Memoization helper
export function memoize<T extends (...args: any[]) => any>(fn: T): T {
  const cache = new Map();
  return ((...args: any[]) => {
    const key = JSON.stringify(args);
    if (cache.has(key)) {
      return cache.get(key);
    }
    const result = fn(...args);
    cache.set(key, result);
    return result;
  }) as T;
}
```

**Add to package.json scripts:**
```json
{
  "scripts": {
    "test": "jest",
    "test:perf": "react-native-performance",
    "analyze": "npx expo-analyze"
  }
}
```

**Create basic test file: __tests__/Block.test.ts**
```typescript
import { createBlock, stackBlock, updateBlock } from '../utils/Block';
import { GAME } from '../constants/theme';

describe('Block', () => {
  test('createBlock creates valid first block', () => {
    const block = createBlock(0, null, 0);
    expect(block.width).toBe(GAME.INITIAL_BLOCK_WIDTH);
    expect(block.isMoving).toBe(true);
  });

  test('stackBlock succeeds on perfect alignment', () => {
    const target = createBlock(0, null, 0);
    target.x = 100;
    target.isMoving = false;

    const moving = createBlock(1, target, 1);
    moving.x = 100; // Perfect alignment

    const result = stackBlock(moving, target);
    expect(result.success).toBe(true);
    expect(result.isPerfect).toBe(true);
  });

  test('stackBlock fails on complete miss', () => {
    const target = createBlock(0, null, 0);
    target.x = 100;
    target.width = 100;
    target.isMoving = false;

    const moving = createBlock(1, target, 1);
    moving.x = 300; // Complete miss
    moving.width = 100;

    const result = stackBlock(moving, target);
    expect(result.success).toBe(false);
  });
});
```

---

## Task 18: Final polish and app store preparation

Prepare the app for release.

1. **Update app.json with final metadata:**
```json
{
  "expo": {
    "name": "Tower Stack",
    "slug": "tower-stack",
    "version": "1.0.0",
    "description": "Addictive block stacking game. Stack as high as you can!",
    "githubUrl": "https://github.com/yourname/tower-stack",
    "privacy": "public",
    "platforms": ["ios", "android"],
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "cover",
      "backgroundColor": "#1a1a2e"
    },
    "updates": {
      "fallbackToCacheTimeout": 0
    },
    "assetBundlePatterns": ["**/*"],
    "ios": {
      "supportsTablet": false,
      "bundleIdentifier": "com.yourname.towerstack",
      "buildNumber": "1",
      "config": {
        "googleMobileAdsAppId": "ca-app-pub-XXXXXXXX~XXXXXXXX"
      }
    },
    "android": {
      "package": "com.yourname.towerstack",
      "versionCode": 1,
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#1a1a2e"
      },
      "config": {
        "googleMobileAdsAppId": "ca-app-pub-XXXXXXXX~XXXXXXXX"
      }
    },
    "plugins": [
      "expo-router",
      [
        "react-native-google-mobile-ads",
        {
          "androidAppId": "ca-app-pub-XXXXXXXX~XXXXXXXX",
          "iosAppId": "ca-app-pub-XXXXXXXX~XXXXXXXX"
        }
      ]
    ]
  }
}
```

2. **Create PRIVACY.md for app store:**
   - Data collected: None (game data stored locally)
   - Ads: Google AdMob (personalized/non-personalized)
   - Analytics: None

3. **Create store listing text:**
   - Title: Tower Stack - Block Stacking Game
   - Short description: Stack blocks perfectly. How high can you go?
   - Keywords: stacking game, blocks, tower, arcade, casual, addictive

4. **Run final checks:**
```bash
npx expo doctor
npm run lint
npm test
npx expo export --platform all
```

---

## Summary

**Total Tasks**: 18 detailed tasks
**Estimated overnight sessions**: 2-3 nights

**What you'll have:**
- Polished, addictive stacking game
- AdMob integration (interstitials + rewarded)
- Sound & haptic feedback
- High score persistence
- Daily challenges & streaks
- Tutorial for new players
- App store ready

**Ad Revenue Points:**
1. Interstitial every 3 games
2. Rewarded video to continue after game over
3. Rewarded video to double final score

**Engagement Hooks:**
- Perfect streak bonuses
- Daily challenge targets
- High score chasing
- Progressive difficulty

Run with:
```bash
./overnight.py --project ~/projects/tower-stack --tasks mobile-game-tasks.md
```
