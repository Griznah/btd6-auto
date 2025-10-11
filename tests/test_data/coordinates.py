# Test coordinate data for validation testing
VALID_COORDINATES = [
    (100, 100),
    (500, 300),
    (1200, 800),
    (0, 0),
    (1920, 1080),
]

INVALID_COORDINATES = [
    (-10, -10),      # Negative coordinates
    (2000, 1200),    # Beyond typical screen resolution
    ("100", "200"),  # String coordinates
    (100,),          # Single value tuple
    (100, 200, 300), # Triple value tuple
    None,            # None value
    [100, 200],      # List instead of tuple
]

CONFLICTING_COORDINATES = [
    (100, 100),
    (105, 105),  # Very close to first
    (110, 110),  # Close to first
    (500, 500),  # Far from others
    (102, 102),  # Close to first
]

SCREEN_RESOLUTIONS = [
    (1920, 1080),  # Full HD
    (2560, 1440),  # 1440p
    (3840, 2160),  # 4K
    (1366, 768),   # Laptop resolution
    (800, 600),    # Low resolution
]

EDGE_CASE_COORDINATES = [
    (0, 0),                    # Top-left corner
    (1919, 1079),             # Bottom-right corner (1920x1080)
    (960, 540),               # Center of 1920x1080
    (1, 1),                   # Just inside bounds
    (1918, 1078),             # Just inside bottom-right
]
