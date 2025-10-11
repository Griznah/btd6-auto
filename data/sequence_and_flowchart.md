# Sequence and flowchart

sequenceDiagram
    participant User
    participant Bot
    participant Game

    User->>Bot: Start bot
    Bot->>Game: Launch BTD6
    Note right of Bot: Pause: 10-30s (game load)

    Bot->>Game: Detect game state
    Note right of Bot: Pause: 2-5s (UI detection)

    Bot->>Game: Select map/hero/towers
    Note right of Bot: Pause: 2-10s (menu navigation)

    Bot->>Game: Start game round
    Note right of Bot: Pause: 1-3s (round start)

    Bot->>Game: Place towers
    Note right of Bot: Pause: 1-2s per tower (placement animation)

    Bot->>Game: Upgrade towers
    Note right of Bot: Pause: 1-2s per upgrade (animation)

    Bot->>Game: Use abilities
    Note right of Bot: Pause: 5-30s (ability cooldown)

    Bot->>Game: Monitor game progress
    Note right of Bot: Pause: 30-300s (round duration)

    Bot->>Game: Handle end of game
    Note right of Bot: Pause: 2-5s (end screen)

    Bot->>User: Report results / restart / exit

flowchart TD
        A[Start Bot] --> B[Launch BTD6<br>Pause: 10-30s]
        B --> C[Detect Game State<br>Pause: 2-5s]
        C --> D[Select Map/Hero/Towers<br>Pause: 2-10s]
        D --> E[Start Game Round<br>Pause: 1-3s]
        E --> F[Place Towers<br>Pause: 1-2s each]
        F --> G[Upgrade Towers<br>Pause: 1-2s each]
        G --> H[Use Abilities<br>Pause: 5-30s]
        H --> I[Monitor Progress<br>Pause: 30-300s]
        I --> J[Handle End of Game<br>Pause: 2-5s]
        J --> K[Report/Restart/Exit]
