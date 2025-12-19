# Arjun Tambe, Shuban Nanisetty, Charanjit Kukkadapu
# Final Project: Chr icles of Time level 1 
#Our game features an interactive based free map in which they can interact with bosses npcs and buy stuff, they have to compelte quests in order to progress to the next level.

import pygame
import traceback
import os
import math
import random

# core game loop for Chronicles of Time: handles movement, combat, UI, and progression.

pygame.init()
# Initialize mixer separately to avoid crashes if audio device is missing
try:
    pygame.mixer.init()
except Exception:
    pass
os.chdir(os.path.dirname(__file__) if __file__ else os.getcwd())

#  game constants
ROOM_WIDTH = 800    
ROOM_HEIGHT = 800
GRID_WIDTH = 3
GRID_HEIGHT = 3
LEVELS = 3
DEV_MODE = True # this is for debugging and adding invisible barriers so that we can see where they are
DEV_SKIP_TO_LEVEL_2 = True  
# Level 2 spawn point (consistent spawn when entering Level 2)
LEVEL2_SPAWN = (ROOM_WIDTH // 2, ROOM_HEIGHT // 2)
# ------------ LEVEL 2 (CYBERPUNK) ------------
LEVEL_2_NAME = "The Neon City (Cyberpunk Future)"
LEVEL_2_BG_MAP = {               # (row,col) : filename  (no extension)
    (0,0): "rooftop_hideout",
    (0,1): "alley_market",
    (0,2): "data_hub",
    (1,0): "subway_tunnels",
    (1,1): "neon_streets",
    (1,2): "factory_exterior",
    (2,0): "core_reactor_room",
    (2,1): "time_gateway",
    (2,2): "ai_control_room",
}
#  setup
screen = pygame.display.set_mode((ROOM_WIDTH, ROOM_HEIGHT))
pygame.display.set_caption("Chronicles of Time")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 30)
title_font = pygame.font.SysFont(None, 70)
small_font = pygame.font.SysFont(None, 24)
button_font = pygame.font.SysFont(None, 40)
POINTER_COLOR = (255, 215, 0)
POINTER_SIZE = 12
POINTER_OFFSET_X = -20


# damgage zone
damage_zones = []
damage_timer = 0.0
DAMAGE_INTERVAL = 1.0  

#  player setup (ultra-small hitbox for maximum squeezing past obstacles)
player = pygame.Rect(400, 400, 20, 25) 
# render size can be larger than hitbox so the player appears bigger on screen
PLAYER_RENDER_WIDTH = 80
PLAYER_RENDER_HEIGHT = 100
player_speed = 7
current_room = [0, 0, 0]
previous_room = tuple(current_room)
player_direction = "right"  
PLAYER_ANIM_SPEED = 0.08  # seconds per frame when moving
player_anim_frames = {}
player_anim_state = "idle"
player_anim_index = 0
player_anim_timer = 0.0
# weapon system
bullets = []
ammo = 0  
max_ammo = 30
reload_time = 0.0
is_reloading = False
player_angle = 0.0
shoot_cooldown = 0.0
has_weapon = False  


is_laser_weapon = False 
laser_cooldown = 0.0  
LASER_COOLDOWN_TIME = 0.1  
REGULAR_COOLDOWN_TIME = 0.2  
# Track how many ammo packs have been bought per level (level 0 and level 1)
ammo_packs_bought = {0: 0, 1: 0}
# Maximum number of ammo packs allowed per level
MAX_AMMO_PACKS = 5

#  shop items
blacksmith_items = {
    "weapon": {
        "name": "Basic Firearm",
        "description": "",
        "cost": 20,
        "purchased": False,
        "type": "weapon"
    },
    "ammo_pack": {
        "name": "Ammo Pack",
        "description": "",
        "cost": 10,
        "purchased": False,
        "type": "consumable"
    },
    "health_potion": {
        "name": "Health Potion", 
        "description": "",
        "cost": 15,
        "purchased": False,
        "type": "consumable"
    },
    "armor_upgrade": {
        "name": "Armor Upgrade",
        "description": "",
        "cost": 25,
        "purchased": False,
        "type": "upgrade"
    },
    "weapon_upgrade": {
        "name": "Weapon Upgrade", 
        "description": "",
        "cost": 30,
        "purchased": False,
        "type": "upgrade"
    },  # ← ADD COMMA HERE
    "cyber_weapon": {
        "name": "Neon Blaster",
        "description": "High-tech firearm",
        "cost": 50,
        "purchased": False,
        "type": "weapon",
        "cyber_only": True,
        "damage_boost": 15
    },
    "cyber_armor": {
        "name": "Energy Shield",
        "description": "Advanced armor",
        "cost": 40,
        "purchased": False,
        "type": "upgrade",
        "cyber_only": True,
        "health_boost": 50
    },
    "cyber_ammo": {
        "name": "Energy Cells",
        "description": "Ammo for blaster",
        "cost": 20,
        "purchased": False,
        "type": "consumable",
        "cyber_only": True,
        "ammo_amount": 50
    },
    "cyber_potion": {
        "name": "Nanite Heal",
        "description": "Advanced healing",
        "cost": 25,
        "purchased": False,
        "type": "consumable",
        "cyber_only": True,
        "heal_amount": 50
    }
}


#  upgrade system
upgrade_costs = {
    "weapon": {1: 30, 2: 50, 3: 75, 4: 100, 5: 150},
    "armor": {1: 25, 2: 45, 3: 70, 4: 95, 5: 130}
}
# Maximum upgrade caps
ARMOR_MAX_LEVEL = 5
    
#  simple image loading with caching and placeholders
ASSETS_DIR = "assets"
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
image_cache = {}
sound_cache = {}

def load_sound(name):
    """Load a sound if it exists (tries wav/mp3/ogg), otherwise return None (safe no-op)."""
    candidates = []
    root, ext = os.path.splitext(name)
    if ext:
        candidates.append(name)
    else:
        candidates.extend([f"{root}.wav", f"{root}.mp3", f"{root}.ogg"])
    for candidate in candidates:
        path = os.path.join(SOUNDS_DIR, candidate)
        if not os.path.exists(path):
            continue
        cache_key = candidate
        if cache_key in sound_cache:
            return sound_cache[cache_key]
        try:
            snd = pygame.mixer.Sound(path)
            sound_cache[cache_key] = snd
            return snd
        except Exception:
            continue
    return None

def play_sound(snd):
    """Play a sound safely."""
    if snd:
        try:
            snd.play()
        except Exception:
            pass

# pre-load core sounds after helpers exist
GUNSHOT_SOUND = load_sound("gunshot")
LASER_SOUND = load_sound("laser")

def _placeholder_color(name: str):
    """Pick a sensible placeholder color based on asset name."""
    name = name.lower()
    if "background" in name:
        return (70, 100, 140)
    if "character" in name or "npc" in name:
        return (80, 140, 200)
    if "tree" in name:
        return (60, 140, 60)
    if "rock" in name or "bridge" in name:
        return (120, 120, 120)
    if "rune" in name:
        return (120, 80, 180)
    if "bookshelf" in name:
        return (140, 100, 60)
    if "key" in name:
        return (230, 200, 70)
    if "portal" in name:
        return (120, 180, 220)
    if "campfire" in name:
        return (200, 120, 60)
    if "anvil" in name or "cage" in name:
        return (100, 100, 130)
    if "potion" in name:
        return (180, 60, 60)
    if "herb" in name:
        return (60, 160, 100)
    if "gold" in name:
        return (230, 200, 50)
    if "boss" in name:
        return (180, 60, 60)
    if "timeshard" in name:
        return (150, 150, 255)
    return (140, 140, 140)

def create_placeholder(name, width, height):
    """Create a non-magenta placeholder so missing assets are less jarring."""
    w = width or 50
    h = height or 50
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    color = _placeholder_color(name)
    surf.fill(color)
    pygame.draw.rect(surf, (20, 20, 20), surf.get_rect(), 2)
    return surf

def _auto_transparent_bg(img):
    """If an image lacks alpha, treat the corner color as a colorkey."""
    if img.get_flags() & pygame.SRCALPHA or img.get_alpha() is not None:
        return img
    w, h = img.get_size()
    corner_color = img.get_at((0, 0))[:3]
    corners = [
        corner_color,
        img.get_at((w - 1, 0))[:3],
        img.get_at((0, h - 1))[:3],
        img.get_at((w - 1, h - 1))[:3],
    ]
    if all(c == corner_color for c in corners):
        img = img.convert()
        img.set_colorkey(corner_color)
        img = img.convert_alpha()
    return img

def load_image(name, width=None, height=None):
    """Image loader with caching and readable placeholders."""
    cache_key = f"{name}_{width}x{height}" if width and height else name
    
    if cache_key in image_cache:
        return image_cache[cache_key]
    
    try:
        filepath = os.path.join(ASSETS_DIR, name)
        if os.path.exists(filepath):
           
            try:
                img = pygame.image.load(filepath).convert_alpha() # this makes sure that all images load properly
            except:
                img = _auto_transparent_bg(pygame.image.load(filepath).convert())
            else:
                img = _auto_transparent_bg(img)
            
            if width and height:
                img = pygame.transform.scale(img, (width, height))
            image_cache[cache_key] = img
            return img
    except:
        pass


    fallback = create_placeholder(name, width, height)
    try:
        image_name = name.split('/')[-1].split('.')[0]
        label_font = pygame.font.SysFont(None, max(12, min(20, fallback.get_width() // 5)))
        text = label_font.render(image_name, True, (255, 255, 255))
        text_rect = text.get_rect(center=(fallback.get_width() // 2, fallback.get_height() // 2))
        bg_rect = text_rect.inflate(10, 5)
        pygame.draw.rect(fallback, (0, 0, 0, 180), bg_rect)
        pygame.draw.rect(fallback, (255, 255, 255), bg_rect, 1)
        fallback.blit(text, text_rect)
    except:
        pass
    image_cache[cache_key] = fallback
    return fallback

def load_smart_bg(level, row, col):
    """Return Surface for any level, or None if no file."""
    if level == 0:   # your existing level-1 map
        background_mapping = {
            (0, 0, 0): "village",
            (0, 0, 1): "blacksmith",
            (0, 0, 2): "forestPath",
            (0, 1, 0): "goblincamp",
            (0, 1, 1): "castlebridge",
            (0, 1, 2): "UpdatedCastleCourt",
            (0, 2, 0): "throneroom",
            (0, 2, 1): "library",
            (0, 2, 2): "portalUpdated1",
        }
        room_type = background_mapping.get((level, row, col))
        if room_type:
            return load_image(f"backgrounds/{room_type}.png", ROOM_WIDTH, ROOM_HEIGHT)
        return None
    elif level == 1:   # ------------- LEVEL 2 -------------
        filename = LEVEL_2_BG_MAP.get((row, col))
        if filename:
            return load_image(f"backgrounds/{filename}.png", ROOM_WIDTH, ROOM_HEIGHT)
        return None
    return None



def _load_player_sheet(filename):
    """Slice a horizontal sprite sheet into frames scaled to the player rect."""
    sheet_path = os.path.join(ASSETS_DIR, "characters", "New Folder With Items", filename)
    try:
        sheet = pygame.image.load(sheet_path).convert_alpha()
    except Exception:
        return []
    
    frame_height = sheet.get_height()
    frame_width = frame_height  # sheets are square and laid out horizontally
    
    cols = max(1, sheet.get_width() // frame_width)
    frames = []
    for i in range(cols):
        frame_rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
        frame = sheet.subsurface(frame_rect).copy()
        frame = pygame.transform.scale(frame, (PLAYER_RENDER_WIDTH, PLAYER_RENDER_HEIGHT))
        frames.append(frame)
    return frames

def _ensure_player_frames():
    """Load and cache player idle/run animations (left/right)."""
    global player_anim_frames
    if player_anim_frames:
        return player_anim_frames
    
    idle_frames = _load_player_sheet("Idle.png")
    run_frames = _load_player_sheet("Run.png")
    
    # fall back to old single sprite if sheets fail to load
    if not idle_frames:
        idle_frames = [load_image("characters/player_right.png", PLAYER_RENDER_WIDTH, PLAYER_RENDER_HEIGHT)]
    if not run_frames:
        run_frames = idle_frames
    
    player_anim_frames = {
        "idle_right": idle_frames,
        "idle_left": [pygame.transform.flip(f, True, False) for f in idle_frames],
        "run_right": run_frames,
        "run_left": [pygame.transform.flip(f, True, False) for f in run_frames],
    }
    return player_anim_frames

def load_player_image(direction="right"):
    """Load player sprite based on direction (only left/right supported)."""
    _ensure_player_frames()
    key = f"idle_{direction}"
    frames = player_anim_frames.get(key) or []
    return frames[0] if frames else load_image(f"characters/player_{direction}.png", PLAYER_RENDER_WIDTH, PLAYER_RENDER_HEIGHT)

def load_object_image(obj_type, width, height):
    return load_image(f"objects/{obj_type}.png", width, height)

def load_item_image(item_type):
    """Load items with larger size for keys, gold, and herbs."""
    if item_type == "key":
        return load_image(f"items/{item_type}.png", 45, 45)  
    elif item_type == "gold":
        return load_image(f"items/{item_type}.png", 45, 45)  
    elif item_type == "herb":
        return load_image(f"items/{item_type}.png", 45, 45)  
    elif item_type == "timeshard":
        return load_image(f"items/{item_type}.png", 50, 50)  
    elif item_type == "keycard":
        return load_image(f"items/keycard.png", 45, 45)
    elif item_type == "credit":
        return load_image(f"items/credit.png", 36, 36)
    return load_image(f"items/{item_type}.png", 25, 25)

def get_npc_size(npc_type):
    """Return sprite size overrides for specific NPCs."""
    if npc_type == "goblin":
        return (50, 70)
    elif npc_type == "boss1":
        return (100, 120) 
    elif npc_type == "herbcollector":
        return (70, 90)  
    elif npc_type == "knight":
        return (50, 70) 
    elif npc_type == "timebandit":
        return (70, 100)
    elif npc_type == "boss2":
        return (110, 130)
    return (35, 55)

def load_npc_image(npc_type):
    size = get_npc_size(npc_type)
    # try singular filename first, then plural (some assets may be named 'timebandits.png')
    primary = f"npcs/{npc_type}.png"
    plural = f"npcs/{npc_type}s.png"
    primary_path = os.path.join(ASSETS_DIR, primary)
    plural_path = os.path.join(ASSETS_DIR, plural)
    if os.path.exists(primary_path):
        return load_image(primary, size[0], size[1])
    if os.path.exists(plural_path):
        return load_image(plural, size[0], size[1])
    return load_image(primary, size[0], size[1])

def load_axe_image():
    """Load the boss axe image."""
    return load_image("npcs/axe.png", 90, 50) 

#  game state
health = 100
max_health = 100
weapon_level = 1
armor_level = 0
GOBLIN_CONTACT_DAMAGE = 10
goblin_contact_cooldown = 0.0  
player_speed_boost_timer = 0.0
player_electrified_timer = 0.0  # Electrify status effect (slows player)
# Time Bandit base stats
TIMEBANDIT_BASE_HP = 50
TIMEBANDIT_BASE_DAMAGE = 10

#  inventory system
# initial player inventory
inventory = {
    "Gold": 50,
    "Health Potions": 3,
    "Herbs": 0,
    "Keys": 0,
    "Time Shards": 0
}
# Track ammo packs (count of consumable packs)
inventory.setdefault("Ammo Packs", 0)
# initial quests (may be updated when entering levels)
# Predefine common quest entries to avoid KeyError when updating status
quests = {
    "buy_weapon": {"active": False, "complete": False, "description": "Buy a basic firearm from the Blacksmith"},
    "upgrade_sword": {"active": False, "complete": False, "description": "Upgrade your weapon at the Blacksmith"},
    "buy_laser_weapon": {"active": False, "complete": False, "description": "Buy a Neon Blaster from the Neon Market"},
    "upgrade_laser": {"active": False, "complete": False, "description": "Upgrade your laser weapon"},
    "upgrade_energy_shield": {"active": False, "complete": False, "description": "Upgrade your energy shield in the Neon Market"},
    "defeat_goblin_king": {"active": False, "complete": False, "description": "Defeat the Goblin King in the throne room"},
    "find_shard_1": {"active": False, "complete": False, "description": "Find the first Time Shard"},
    "rescue_knight": {"active": False, "complete": False, "description": "Rescue the knight trapped in the cage"},
    "talk_to_elder": {"active": False, "complete": False, "description": "Speak with Elder Rowan in the village"},
    "kill_time_bandits": {"active": False, "complete": False, "description": "Eliminate the Time Bandits in Neon Streets"},
    "solve_drawbridge": {"active": False, "complete": False, "description": "Solve the drawbridge puzzle"},
    "collect_herbs": {"active": False, "complete": False, "description": "Collect 3 herbs for the Herb Collector"}
}
#   collected items tracking
collected_gold = set()
collected_herbs = set()
collected_potions = set()
collected_keys = set()
collected_timeshards = set()
collected_credits = set()

#  safe system
safe_code = "4231" 
safe_input = ""
safe_unlocked = False
safe_visible = False

#  Data Hub cipher system
cipher_plain = "I am Bon Bon"
cipher_visible = False
cipher_input = ""
cipher_shift = 0
cipher_text_shifted = ""

def caesar_shift(text, shift):
    out = []
    for ch in text:
        if ch.isalpha():
            base = 'A' if ch.isupper() else 'a'
            out.append(chr((ord(ch) - ord(base) + shift) % 26 + ord(base)))
        else:
            out.append(ch)
    return ''.join(out)

def start_cipher():
    global cipher_shift, cipher_text_shifted, cipher_input, cipher_visible
    cipher_shift = random.randint(1, 25)
    cipher_text_shifted = caesar_shift(cipher_plain, cipher_shift)
    cipher_input = ""
    cipher_visible = True
    set_message("Data Hub activated: decode the message", (0, 200, 255), 3.0)

def handle_cipher_key(event):
    """Handle key input while cipher overlay is active."""
    global cipher_input, cipher_visible
    # BACKSPACE
    if event.key == pygame.K_BACKSPACE:
        cipher_input = cipher_input[:-1]
        return
    # ESC closes
    if event.key == pygame.K_ESCAPE:
        cipher_visible = False
        return
    # Enter to submit
    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
        if cipher_input.strip().lower() == cipher_plain.lower():
            cipher_visible = False
            # spawn a keycard pickup to the side of the Data Hub
            room_key = tuple(current_room)
            room_info = room_data.get(room_key, {})
            # Spawn keycard to the right side of the room
            keycard_x = ROOM_WIDTH - 100
            keycard_y = ROOM_HEIGHT // 2
            room_info.setdefault("items", []).append({"type": "keycard", "x": keycard_x, "y": keycard_y, "id": f"keycard_datahub_{room_key[1]}_{room_key[2]}"})
            set_message("Correct! A Keycard has been spawned in the Data Hub.", (0, 255, 0), 3.0)
        else:
            set_message("Incorrect. Try again.", (255, 0, 0), 1.5)
            cipher_input = ""
        return

    # Accept letters and spaces
    if len(event.unicode) == 1 and (event.unicode.isalpha() or event.unicode.isspace()):
        cipher_input += event.unicode

# maze system
maze_visible = False
maze_completed = False
maze_player_pos = [1, 1]  
maze_exit_pos = [9, 9]    
maze_cell_size = 40
maze_width = 11
maze_height = 11

maze_layout = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1],
    [1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]

#  boss system
boss = None
boss_health = 0
boss_max_health = 0
boss_attack_cooldown = 0
boss_axe = None
boss_axe_angle = 0
boss_axe_swinging = False
boss_axe_damage = 80  # boss does 80 damage per hit
boss_defeated = False
boss_drop_collected = False
boss_phase = 1  
boss_thrown_axes = []  
boss_throw_cooldown = 0


game_state = "main_menu" 
on_home = True
hud_visible = False
map_visible = False
quest_log_visible = False
dialogue_active = False
current_dialogue = []
dialogue_index = 0
upgrade_shop_visible = False
in_combat = False
combat_enemies = []
give_herbs_active = False
cyber_shop_visible = False  #

#  messages
message = ""
message_timer = 0.0
message_color = (255, 255, 255)

#  npc dialogues
npc_dialogues = {
    (0, 0, 0, "elder"): [
        "Elder Rowan: Welcome, brave Arin!",
        "Elder Rowan: The Time Shards have been scattered across eras.",
        "Elder Rowan: You'll need protection for your journey.",
        "Elder Rowan: Visit the Blacksmith to the east - he can sell you a weapon.",
        "Elder Rowan: A basic firearm costs 20 gold pieces.",
        "Elder Rowan: He also offers armor and weapon upgrades for your journey.",
        "Quest Updated: Visit the Blacksmith to buy a weapon"
    ],
    (0, 1, 0, "knight"): [  
        "Knight Aelric: Please, help me! I'm trapped in this cage!",
        "Knight Aelric: The goblins captured me after the battle.",
        "Knight Aelric: There's a lock mechanism on the cage - can you solve it?",
        "Hint: Interact with the cage to try the lock puzzle"
    ],
    (0, 1, 0, "knight_rescued"): [  
        "Knight Aelric: Thank you for rescuing me!",
        "Knight Aelric: The Goblin King holds the first Time Shard.",
        "Knight Aelric: I dropped my key when they captured me - you should find it nearby.",
        "Quest Updated: Defeat the Goblin King"
    ],
    (0, 2, 1, "herbcollector"): [
        "Herb Collector: Ah, a traveler! I collect rare herbs from the forest.",
        "Herb Collector: If you bring me 3 herbs, I can give you something useful.",
        "Herb Collector: I know the combination to the safe in this room."
    ],
    (0, 2, 1, "herbcollector_with_herbs"): [
        "Herb Collector: Wonderful! You found the herbs!",
        "Herb Collector: As promised, here's the safe combination: 4231",
        "Herb Collector: The safe contains something valuable for your journey.",
        "Quest Updated: Safe combination received!"
    ],(1, 0, 0, "cyber_guide"): [
        "Cyber Guide: Welcome to the Neon City, time traveler!",
        "Cyber Guide: This is the year 2187 - technology has evolved.",
        "Cyber Guide: You'll need advanced weapons here. Visit the Alley Market.",
        "Cyber Guide: They sell laser weapons with rapid fire rates.",
        "Cyber Guide: Be warned — Time Bandits have infested the Neon Streets and Core Reactor area.",
        "Cyber Guide: Clear them out and return for a reward.",
        "Quest Updated: Buy a laser weapon from Neon Market"
    ],
    (1, 0, 1, "market_vendor"): [
        "Market Vendor: Need some firepower, stranger?",
        "Market Vendor: Our laser weapons fire 2x faster than old ballistic guns.",
        "Market Vendor: They use energy cells instead of traditional ammo.",
        "Market Vendor: The Neon Blaster is our best seller - 50 credits."
    ],
}

#   colliders
colliders = []
gold_items = []
herbs = []
potions = []
npcs = []
interactive_objects = []
goblin_rooms = {}

# dynamic NPC states (position, roaming target, talking flag)
npc_states = {}

GOBLIN_WAVES = {
    (0, 0, 2): [
        [(350, 350), (200, 420)],  
        [(450, 260), (280, 520), (600, 420)],  
        [(180, 180), (520, 180), (420, 620)], 
    ],
    (0, 1, 0): [
        [(100, 100), (200, 150), (300, 200), (400, 150), (500, 100)],  
    ],
    (0, 1, 2): [
        [(520, 360), (620, 480)],  
    ],
}

def _init_goblin_rooms():
    """Prepare goblin wave state for configured rooms."""
    for room_key, waves in GOBLIN_WAVES.items():
        goblin_rooms[room_key] = {
            "waves": waves,
            "wave_index": 0,
            "active": [],
            "respawn": 0.0,  
        }

_init_goblin_rooms()

# -------------------- Time Bandits (Cyber Level) --------------------
TIMEBANDIT_WAVES = {
    # Neon Streets (Level 1, row 1, col 1)
    (1, 1, 1): [
        [(220, 220), (520, 300)],
        [(180, 420), (600, 200), (360, 520)],
    ],
    # Core Reactor Room (Level 1, row 2, col 0) - same wave patterns as Neon Streets
    (1, 2, 0): [
        [(220, 220), (520, 300)],
        [(180, 420), (600, 200), (360, 520)],
    ],
}

timebandit_rooms = {}

def _init_timebandits():
    """Prepare time-bandit wave state for configured rooms."""
    for room_key, waves in TIMEBANDIT_WAVES.items():
        timebandit_rooms[room_key] = {
            "waves": waves,
            "wave_index": 0,
            "active": [],
            "respawn": 0.0,
            "key_given": False,
        }

_init_timebandits()

# room data, this uses a dictionary to define room layouts and contents
room_data = {

    # LEVEL 0  –  medieval world

    (0, 0, 0): {
        "name": "Village Square",
        "objects": [
            {"type": "invisible", "x": 110, "y": 100, "width": 140, "height": 600},
            {"type": "invisible", "x": 570, "y": 100, "width": 140, "height": 600},
            {"type": "invisible", "x": 310, "y": 100, "width": 200, "height": 170},
        ],
        "interactive": [],
        "npcs": [
            {"id": "elder", "x": 400, "y": 600, "name": "Elder Rowan"},
        ],
        "items": [
            {"type": "gold", "x": 40, "y": 300, "id": "gold_0_0_0_1"},
            {"type": "gold", "x": 450, "y": 40, "id": "gold_0_0_0_2"},
        ]
    },

    (0, 0, 1): {
        "name": "Blacksmith's Forge",
        "objects": [
            {"type": "invisible", "x": 190, "y": 180, "width": 70, "height": 450},
            {"type": "invisible", "x": 540, "y": 180, "width": 70, "height": 450},
            {"type": "invisible", "x": 250, "y": 170, "width": 340, "height": 70}
        ],
        "interactive": [
            {"type": "anvil", "x": 370, "y": 350, "width": 90, "height": 60},
        ],
        "npcs": [],
        "items": [
            {"type": "gold", "x": 100, "y": 200, "id": "gold_0_0_1_1"},
            {"type": "gold", "x": 700, "y": 300, "id": "gold_0_0_1_2"},
        ]
    },

    (0, 0, 2): {
        "name": "Forest Path",
        "objects": [
            {"type": "tree", "x": 150, "y": 150, "width": 60, "height": 100},
            {"type": "tree", "x": 500, "y": 250, "width": 60, "height": 100},
            {"type": "tree", "x": 250, "y": 500, "width": 60, "height": 100},
            {"type": "tree", "x": 600, "y": 600, "width": 60, "height": 100},
        ],
        "interactive": [],
        "npcs": [
            {"id": "goblin", "x": 350, "y": 350, "name": "Goblin Scout"},
            {"id": "goblin", "x": 200, "y": 420, "name": "Goblin Scout"},
        ],
        "items": [
            {"type": "herb", "x": 300, "y": 300, "id": "herb_0_0_2_1"},
            {"type": "herb", "x": 550, "y": 150, "id": "herb_0_0_2_2"},
            {"type": "herb", "x": 450, "y": 600, "id": "herb_0_0_2_3"},
        ]
    },

    (0, 1, 0): {
        "name": "Goblin Camp",
        "objects": [
            {"type": "rock", "x": 20, "y": 100, "width": 50, "height": 50},
            {"type": "rock", "x": 650, "y": 250, "width": 50, "height": 50},
            {"type": "damage", "x": 325, "y": 340, "width": 160, "height": 150},
            {"type": "invisible", "x": 405, "y": 185, "width": 100, "height": 100},
        ],
        "interactive": [
            {"type": "cage", "x": 100, "y": 500, "width": 120, "height": 120},
        ],
        "npcs": [
            {"id": "knight", "x": 130, "y": 530, "name": "Knight Aelric", "rescued": False},
        ],
        "items": [
            {"type": "potion", "x": 150, "y": 350, "id": "potion_0_1_0_1"},
 
            {"type": "gold", "x": 600, "y": 400, "id": "gold_0_1_0_1"},
        ]
    },

    (0, 1, 1): {
        "name": "Castle Bridge",
        "objects": [
            {"type": "rock", "x": 100, "y": 350, "width": 80, "height": 80},
            {"type": "rock", "x": 620, "y": 350, "width": 80, "height": 80},
        ],
        "interactive": [
            {"type": "lever", "x": 700, "y": 350, "width": 40, "height": 60},
        ],
        "npcs": [],
        "items": []
    },

    (0, 1, 2): {
        "name": "Castle Courtyard",
        "objects": [
            {"type": "invisible", "x": 580, "y": 255, "width": 195, "height": 200},
            {"type": "invisible", "x": 490, "y": 10, "width": 450, "height": 130}
        ],
        "interactive": [],
        "npcs": [],
        "items": [
            {"type": "potion", "x": 250, "y": 400, "id": "potion_0_1_2_1"},
            {"type": "gold", "x": 550, "y": 350, "id": "gold_0_1_2_1"},
        ]
    },

    (0, 2, 0): {
        "name": "Throne Room",
        "objects": [],
        "interactive": [],
        "npcs": [
            {"id": "boss1", "x": 350, "y": 300, "name": "Goblin King"},
        ],
        "items": [
            {"type": "gold", "x": 100, "y": 150, "id": "gold_0_2_0_1"},
            {"type": "gold", "x": 700, "y": 150, "id": "gold_0_2_0_2"},
        ]
    },

    (0, 2, 1): {
        "name": "Secret Library",
        "objects": [
            {"type": "invisible", "x": 110, "y": 110, "width": 90, "height": 570},
            {"type": "invisible", "x": 620, "y": 110, "width": 90, "height": 570},
            {"type": "invisible", "x": 120, "y": 90, "width": 600, "height": 80}
        ],
        "interactive": [
            {"type": "safe", "x": 350, "y": 300, "width": 100, "height": 100},
        ],
        "npcs": [
            {"id": "herbcollector", "x": 500, "y": 500, "name": "Herb Collector"},
        ],
        "items": [
            {"type": "gold", "x": 250, "y": 400, "id": "gold_0_2_1_1"},
        ]
    },

    (0, 2, 2): {
        "name": "Time Portal",
        "objects": [],
        "interactive": [
            {"type": "portal", "x": 340, "y": 340, "width": 120, "height": 120},
        ],
        "npcs": [],
        "items": []
    },
#Charan 
    # ------------------------------------------------------
    # LEVEL 1  –  cyberpunk / neon city  (EMPTY SHELLS)
    # ------------------------------------------------------
    (1, 0, 0): {
        "name": "Rooftop Hideout",   
        "objects": [{"type": "invisible", "x": 150,   "y": 585, "width": 500, "height": 65},
                   {"type": "invisible", "x": 135,   "y": 275,   "width": 60,  "height": 370},
                   {"type": "invisible", "x": 145,   "y": 275,   "width": 200, "height": 50},
                   {"type": "invisible", "x": 450,   "y": 275,   "width": 200, "height": 50}, 
                   {"type": "invisible", "x": 620, "y": 270,  "width": 40,  "height": 100},
                   {"type": "invisible", "x": 620, "y": 500,  "width": 40,  "height": 100},
                   {"type": "invisible", "x": 0,   "y": 0,   "width": 354, "height": 285},
                   {"type": "invisible", "x": 460,   "y": 0,   "width": 354, "height": 285},
                   {"type": "invisible", "x": 610,   "y": 520, "width": 400, "height": 100},
                   {"type": "invisible", "x": 610,   "y": 300, "width": 400, "height": 100}], 
        "interactive": [], 
        "npcs": [
            {"id": "cyber_guide", "x": 400, "y": 500, "name": "Cyber Guide", "roam_radius": 140, "speed": 40, "stop_distance": 160},
        ], 
        "items": []
    },
  
    (1, 0, 1): {
    "name": "Alley Market", 
    "objects": [
        {"type": "invisible", "x": 0, "y": 40, "width": 230, "height": 350},
        {"type": "invisible", "x": 0, "y": 500, "width": 230, "height": 350},
        {"type": "shop", "x": 500, "y": 400, "width": 100, "height": 100}
    ],
    "interactive": [],
    "npcs": [],
    "items": []
    },
    (1, 0, 2): {"name": "Data Hub",          
                                "objects": [],
                                 "interactive": [
                                         {"type": "datahub", "x": 360, "y": 360, "width": 80, "height": 80}
                                 ],
                                 "npcs": [],
                                     "items": []},
    (1, 1, 0): {"name": "Subway Tunnels",    
                "objects": [
                                                        {"type": "invisible", "x": 143, "y": 710, "width": 225, "height": 75},
                                                        {"type": "invisible", "x": 465, "y": 710, "width": 225, "height": 75}, 
                                                        {"type": "invisible", "x": 100, "y": 375, "width": 150, "height": 75}
                                                     ],
                 "interactive": []
                 , "npcs": [],
                 "items": []},
    (1, 1, 1): {"name": "Neon Streets",      "objects": [{"type": "invisible", "x": 100, "y": 215, "width": 155, "height": 125}],
                 "interactive": []
                 , "npcs": [],
                   "items": []},
    (1, 1, 2): {"name": "Factory Exterior",  
                "objects": [{"type": "invisible", "x": 280, "y": 305, "width": 225, "height": 195},
                            {"type": "invisible", "x": 700, "y": 135, "width": 175, "height": 505},
                            ],
                 "interactive": []
                 , "npcs": [],
                   "items": []},
    (1, 2, 0): {"name": "Core Reactor Room", 
                "objects": [],
                 "interactive": []
                 , "npcs": [],
                   "items": []},
    (1, 2, 1): {"name": "Time Gateway",   
                "objects": [],
                 "interactive": []
                 , "npcs": [],
                   "items": []},
    (1, 2, 2): {"name": "AI Control Room",      
                "objects": [{"type": "invisible", "x": 720, "y": 40, "width": 125, "height": 625},
                            {"type": "invisible", "x": 520, "y": 670, "width": 225, "height": 55},
                            {"type": "invisible", "x": 510, "y": 00, "width": 305, "height": 165}], 
                "interactive": []
                , "npcs": [],
                  "items": []},
}

goblin_states = {}

def _init_goblins():
    """Seed legacy goblin state from room data (initial wave positions)."""
    forest_key = (0, 0, 2)
    forest_info = room_data.get(forest_key, {})
    spawn = []
    for npc in forest_info.get("npcs", []):
        if npc.get("id") == "goblin":
            spawn.append({"x": npc["x"], "y": npc["y"], "alive": True})
    if spawn:
        goblin_states[forest_key] = spawn

_init_goblins()


def _init_npc_states():
    """Initialize dynamic npc state entries for every NPC in room_data.
    Keys: "level_row_col_id_index" to uniquely identify duplicates.
    """
    npc_states.clear()
    for room_key, info in room_data.items():
        npcs_list = info.get("npcs", [])
        for i, npc in enumerate(npcs_list):
            key = f"{room_key[0]}_{room_key[1]}_{room_key[2]}_{npc.get('id')}_{i}"
            # store base/home position and dynamic fields
            state = {
                "room_key": tuple(room_key),
                "id": npc.get("id"),
                "home_x": float(npc.get("x", 0)),
                "home_y": float(npc.get("y", 0)),
                "x": float(npc.get("x", 0)),
                "y": float(npc.get("y", 0)),
                "roam_radius": npc.get("roam_radius", 80),
                "speed": npc.get("speed", 30),  # pixels per second
                "target": None,
                "idle_timer": random.uniform(0.5, 2.5),
                "talking": False,
                "stop_distance": npc.get("stop_distance", 120),
            }
            npc_states[key] = state


_init_npc_states()

# Seed moderate credits across Level 2 so they're always present (2 per room)
def _seed_level2_credits():
    level2_rooms = [(1, r, c) for r in range(3) for c in range(3)]
    for room_key in level2_rooms:
        room_info = room_data.get(room_key, {})
        # don't duplicate if credits already present
        existing = any(it.get("type") == "credit" for it in room_info.get("items", []))
        if existing:
            continue
        # Get invisible barriers for this room to avoid spawning in them
        barriers = [obj for obj in room_info.get("objects", []) if obj.get("type") == "invisible"]
        for i in range(2):
            # Try to find a valid spawn location not in a barrier
            valid = False
            attempts = 0
            while not valid and attempts < 10:
                cx = random.randint(100, ROOM_WIDTH - 100)
                cy = random.randint(100, ROOM_HEIGHT - 100)
                # Check if this point is inside any barrier
                point_rect = pygame.Rect(cx, cy, 1, 1)
                in_barrier = any(point_rect.colliderect(pygame.Rect(b["x"], b["y"], b["width"], b["height"])) for b in barriers)
                valid = not in_barrier
                attempts += 1
            # If we found a valid spot, add the credit
            if valid:
                cid = f"credit_{room_key[1]}_{room_key[2]}_{random.randint(1000,9999)}_{i}"
                room_info.setdefault("items", []).append({"type": "credit", "x": cx, "y": cy, "id": cid})

_seed_level2_credits()

#  BOSS FUNCTIONS 
def init_boss():
    """Initialize the boss in the throne room."""
    global boss, boss_health, boss_max_health, boss_attack_cooldown, boss_axe, boss_axe_angle, boss_defeated, boss_drop_collected, boss_phase, boss_thrown_axes, boss_throw_cooldown
    boss_rect = pygame.Rect(350, 300, 100, 120)
    boss = {
        "rect": boss_rect,
        "alive": True,
        "last_direction": "right"
    }
    boss_max_health = max_health * 4  
    boss_health = boss_max_health
    boss_attack_cooldown = 0
    boss_axe = {"x": 0, "y": 0, "angle": 0, "swinging": False}
    boss_axe_angle = 0
    boss_defeated = False
    boss_drop_collected = False
    boss_phase = 1
    boss_thrown_axes = []
    boss_throw_cooldown = 0

def update_boss(dt):
    """Update boss behavior and attacks."""
    global boss_health, boss_attack_cooldown, boss_axe, boss_axe_angle, boss_axe_swinging, health, boss_defeated, boss_phase, boss_thrown_axes, boss_throw_cooldown
    
    if not boss or not boss["alive"]:
        return
    
    dt_sec = dt / 1000.0
    
    
    if boss_attack_cooldown > 0:
        boss_attack_cooldown -= dt_sec
    if boss_throw_cooldown > 0:
        boss_throw_cooldown -= dt_sec
    
    # boss movement 
    speed = 300  
    dx = player.centerx - boss["rect"].centerx
    dy = player.centery - boss["rect"].centery
    dist = math.hypot(dx, dy)
    
    if dx > 0:
        boss["last_direction"] = "right"
    else:
        boss["last_direction"] = "left"
    
    if dist > 0 and dist < 400:  
        step = speed * dt_sec
        boss["rect"].x += (dx / dist) * step
        boss["rect"].y += (dy / dist) * step
        
        
        boss["rect"].x = max(100, min(ROOM_WIDTH - boss["rect"].width - 100, boss["rect"].x))
        boss["rect"].y = max(100, min(ROOM_HEIGHT - boss["rect"].height - 100, boss["rect"].y))
    
    # phase 1: Melee attacks
    if boss_phase == 1:
        if dist < 180 and boss_attack_cooldown <= 0:
            boss_axe_swinging = True
            boss_axe_angle = 0
            boss_attack_cooldown = 2.5  
    
    # phase 2: Melee + Ranged attacks
    elif boss_phase == 2:
        if dist < 180 and boss_attack_cooldown <= 0:
            boss_axe_swinging = True
            boss_axe_angle = 0
            boss_attack_cooldown = 2.0  
        
        
        if dist > 200 and boss_throw_cooldown <= 0:
            throw_axe()
            boss_throw_cooldown = 3.0  
    
    
    if boss_axe_swinging:
        boss_axe_angle += 8  
        if boss_axe_angle >= 180:
            boss_axe_swinging = False
            boss_axe_angle = 0
            
           
            axe_rect = calculate_axe_rect()
            if player.colliderect(axe_rect):
                damage = boss_axe_damage - (armor_level * 5)  
                if boss_phase == 2:
                    damage += 10  
                health = max(0, health - damage)
                set_message(f"Boss hit you for {damage} damage!", (255, 0, 0), 1.5)
    

    update_thrown_axes(dt_sec)

def throw_axe():
    """Boss throws an axe towards the player in phase 2."""
    if not boss:
        return
    

    dx = player.centerx - boss["rect"].centerx
    dy = player.centery - boss["rect"].centery
    dist = math.hypot(dx, dy)
    
    if dist > 0:
        speed = 400  
        boss_thrown_axes.append({
            "x": float(boss["rect"].centerx),
            "y": float(boss["rect"].centery),
            "dx": (dx / dist) * speed,
            "dy": (dy / dist) * speed,
            "angle": 0
        })
        set_message("Boss throws an axe!", (255, 100, 100), 1.0)

# ===== IMPROVED INVENTORY UI SYSTEM =====
def draw_inventory_hud(surface):
    """Draw a modern, organized inventory HUD that's always visible."""
    # Main HUD background (semi-transparent bar at top)
    hud_height = 110
    hud_bg = pygame.Surface((ROOM_WIDTH, hud_height), pygame.SRCALPHA)
    hud_bg.fill((0, 0, 0, 180))  # Dark semi-transparent
    surface.blit(hud_bg, (0, 0))
    
    # Top border for polish
    pygame.draw.line(surface, (255, 215, 0), (0, hud_height), (ROOM_WIDTH, hud_height), 2)
    
    # Draw in sections
    x_start = 20
    y_start = 15
    section_width = (ROOM_WIDTH - 40) // 4
    
    # SECTION 1: HEALTH & ARMOR
    pygame.draw.rect(surface, (30, 30, 40, 200), (x_start, y_start, section_width, 80))
    pygame.draw.rect(surface, (255, 215, 0), (x_start, y_start, section_width, 80), 2)
    
    # Health bar
    health_bar_width = section_width - 40
    pygame.draw.rect(surface, (100, 0, 0), (x_start + 20, y_start + 20, health_bar_width, 15))
    pygame.draw.rect(surface, (0, 255, 0), (x_start + 20, y_start + 20, 
                                           health_bar_width * (health / max_health), 15))
    pygame.draw.rect(surface, (255, 255, 255), (x_start + 20, y_start + 20, health_bar_width, 15), 1)
    
    # Health text
    health_text = small_font.render(f"HEALTH: {int(health)}/{max_health}", True, (255, 255, 255))
    surface.blit(health_text, (x_start + 20, y_start + 5))
    
    # Armor level
    armor_text = small_font.render(f"ARMOR: LVL {armor_level}", True, (200, 255, 200))
    surface.blit(armor_text, (x_start + 20, y_start + 40))
    
    # SECTION 2: WEAPON & AMMO
    section2_x = x_start + section_width + 10
    pygame.draw.rect(surface, (30, 30, 40, 200), (section2_x, y_start, section_width, 80))
    pygame.draw.rect(surface, (255, 215, 0), (section2_x, y_start, section_width, 80), 2)
    
    weapon_name = "Neon Blaster" if is_laser_weapon else "Firearm" if has_weapon else "None"
    weapon_name_text = small_font.render(f"WEAPON: {weapon_name}", True, (255, 255, 255))
    surface.blit(weapon_name_text, (section2_x + 20, y_start + 5))
    
    # Ammo display
    if has_weapon:
        ammo_text = font.render(f"{ammo}/{max_ammo}", True, (255, 255, 255))
        surface.blit(ammo_text, (section2_x + 30, y_start + 25))
        
        # Ammo bar
        ammo_bar_width = section_width - 60
        pygame.draw.rect(surface, (50, 50, 70), (section2_x + 20, y_start + 50, ammo_bar_width, 8))
        if max_ammo > 0:
            ammo_fill = (ammo / max_ammo) * ammo_bar_width
            ammo_color = (0, 200, 255) if is_laser_weapon else (255, 200, 0)
            pygame.draw.rect(surface, ammo_color, (section2_x + 20, y_start + 50, ammo_fill, 8))
        
        # Reload indicator
        if is_reloading:
            reload_text = small_font.render("RELOADING...", True, (255, 50, 50))
            surface.blit(reload_text, (section2_x + 20, y_start + 62))
    else:
        no_weapon_text = small_font.render("NO WEAPON", True, (255, 100, 100))
        surface.blit(no_weapon_text, (section2_x + 30, y_start + 30))
    
    # SECTION 3: RESOURCES
    section3_x = section2_x + section_width + 10
    pygame.draw.rect(surface, (30, 30, 40, 200), (section3_x, y_start, section_width, 80))
    pygame.draw.rect(surface, (255, 215, 0), (section3_x, y_start, section_width, 80), 2)
    
    # Gold
    gold_icon = load_item_image("gold")
    if gold_icon:
        gold_icon = pygame.transform.scale(gold_icon, (20, 20))
        surface.blit(gold_icon, (section3_x + 15, y_start + 15))
    
    gold_text = small_font.render(f"  {inventory['Gold']}", True, (255, 215, 0))
    surface.blit(gold_text, (section3_x + 40, y_start + 17))
    
    # Keys
    key_icon = load_item_image("key")
    if key_icon:
        key_icon = pygame.transform.scale(key_icon, (20, 20))
        surface.blit(key_icon, (section3_x + 15, y_start + 40))
    
    key_text = small_font.render(f"  {inventory['Keys']}", True, (220, 180, 80))
    surface.blit(key_text, (section3_x + 40, y_start + 42))
    
    # Time Shards
    if inventory['Time Shards'] > 0:
        shard_icon = load_item_image("timeshard")
        if shard_icon:
            shard_icon = pygame.transform.scale(shard_icon, (20, 20))
            surface.blit(shard_icon, (section3_x + 15, y_start + 60))
        
        shard_text = small_font.render(f"  {inventory['Time Shards']}", True, (150, 150, 255))
        surface.blit(shard_text, (section3_x + 40, y_start + 62))
    # Ammo Packs
    packs_text = small_font.render(f"Ammo Packs: {inventory.get('Ammo Packs', 0)}", True, (0, 200, 255))
    surface.blit(packs_text, (section3_x + 80, y_start + 17))
    
    # SECTION 4: CONSUMABLES
    section4_x = section3_x + section_width + 10
    pygame.draw.rect(surface, (30, 30, 40, 200), (section4_x, y_start, section_width, 80))
    pygame.draw.rect(surface, (255, 215, 0), (section4_x, y_start, section_width, 80), 2)
    
    # Potions
    potion_icon = load_item_image("potion")
    if potion_icon:
        potion_icon = pygame.transform.scale(potion_icon, (20, 20))
        surface.blit(potion_icon, (section4_x + 15, y_start + 15))
    
    potion_text = small_font.render(f"  {inventory['Health Potions']}", True, (255, 50, 50))
    surface.blit(potion_text, (section4_x + 40, y_start + 17))
    
    # Herbs
    herb_icon = load_item_image("herb")
    if herb_icon:
        herb_icon = pygame.transform.scale(herb_icon, (20, 20))
        surface.blit(herb_icon, (section4_x + 15, y_start + 40))
    
    herb_text = small_font.render(f"  {inventory['Herbs']}", True, (50, 255, 50))
    surface.blit(herb_text, (section4_x + 40, y_start + 42))
    
    # Quick-use hint
    if inventory['Health Potions'] > 0 and health < max_health:
        hint_text = small_font.render("Press H to use", True, (200, 200, 200))
        surface.blit(hint_text, (section4_x + 15, y_start + 60))


def draw_quick_inventory(surface):
    """Draw a quick-access inventory bar at the bottom."""
    if not hud_visible:  # Only show when inventory is toggled
        return
    
    bar_height = 100
    bar_y = ROOM_HEIGHT - bar_height
    
    # Background
    bar_bg = pygame.Surface((ROOM_WIDTH, bar_height), pygame.SRCALPHA)
    bar_bg.fill((0, 0, 0, 220))
    surface.blit(bar_bg, (0, bar_y))
    
    # Top border
    pygame.draw.line(surface, (255, 215, 0), (0, bar_y), (ROOM_WIDTH, bar_y), 2)
    
    # Section headers
    headers = ["RESOURCES", "QUEST ITEMS", "UPGRADES", "CONSUMABLES"]
    item_width = ROOM_WIDTH // 4
    item_height = 80
    
    for i, header in enumerate(headers):
        x = i * item_width
        header_text = small_font.render(header, True, (255, 215, 0))
        surface.blit(header_text, (x + 10, bar_y + 5))
        
        # Content box
        content_box = pygame.Rect(x + 5, bar_y + 25, item_width - 10, item_height - 30)
        pygame.draw.rect(surface, (40, 40, 60), content_box)
        pygame.draw.rect(surface, (100, 100, 140), content_box, 1)
        
        # Fill with appropriate items
        y_offset = bar_y + 30
        if i == 0:  # Resources
            resource_text = small_font.render(f"Gold: {inventory['Gold']}", True, (255, 215, 0))
            surface.blit(resource_text, (x + 15, y_offset))
        elif i == 1:  # Quest Items
            if inventory['Keys'] > 0:
                key_text = small_font.render(f"Keys: {inventory['Keys']}", True, (220, 180, 80))
                surface.blit(key_text, (x + 15, y_offset))
            if inventory['Time Shards'] > 0:
                shard_text = small_font.render(f"Shards: {inventory['Time Shards']}", True, (150, 150, 255))
                surface.blit(shard_text, (x + 15, y_offset + 20))
        elif i == 2:  # Upgrades
            upgrade_text = small_font.render(f"Weapon Lvl: {weapon_level}", True, (200, 200, 255))
            surface.blit(upgrade_text, (x + 15, y_offset))
            armor_text = small_font.render(f"Armor Lvl: {armor_level}", True, (200, 255, 200))
            surface.blit(armor_text, (x + 15, y_offset + 20))
        elif i == 3:  # Consumables
            if inventory['Health Potions'] > 0:
                potion_text = small_font.render(f"Potions: {inventory['Health Potions']}", True, (255, 50, 50))
                surface.blit(potion_text, (x + 15, y_offset))
            if inventory['Herbs'] > 0:
                herb_text = small_font.render(f"Herbs: {inventory['Herbs']}", True, (50, 255, 50))
                surface.blit(herb_text, (x + 15, y_offset + 20))

# ===== ENHANCED WEAPON HUD =====
def draw_enhanced_weapon_hud(surface):
    """Draw an enhanced weapon HUD with more detailed information."""
    if not has_weapon:
        return
    
    
    panel_width = 180
    panel_height = 100
    panel_x = 10  
    panel_y = 10  
    
    # Panel background
    panel_bg = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel_bg.fill((0, 0, 0, 180))
    pygame.draw.rect(panel_bg, (255, 215, 0), (0, 0, panel_width, panel_height), 2)
    surface.blit(panel_bg, (panel_x, panel_y))
    
    # Weapon icon/type
    weapon_color = (0, 200, 255) if is_laser_weapon else (255, 200, 0)
    weapon_type_text = font.render("LASER" if is_laser_weapon else "FIREARM", True, weapon_color)
    surface.blit(weapon_type_text, (panel_x + 10, panel_y + 10))
    
    # Ammo display with visual bar
    ammo_text = font.render(f"{ammo} / {max_ammo}", True, (255, 255, 255))
    surface.blit(ammo_text, (panel_x + 10, panel_y + 40))
    
    # Ammo bar
    ammo_bar_width = 160
    ammo_bar_height = 10
    ammo_bar_x = panel_x + 10
    ammo_bar_y = panel_y + 70
    
    # Background bar
    pygame.draw.rect(surface, (50, 50, 70), (ammo_bar_x, ammo_bar_y, ammo_bar_width, ammo_bar_height))
    
    # Filled portion
    if max_ammo > 0:
        ammo_percent = ammo / max_ammo
        ammo_fill_width = ammo_bar_width * ammo_percent
        
        if ammo_percent > 0.5:
            fill_color = (0, 200, 0)  # Green for plenty
        elif ammo_percent > 0.25:
            fill_color = (255, 200, 0)  # Yellow for medium
        else:
            fill_color = (255, 50, 0)  # Red for low
            
        if is_laser_weapon:
            fill_color = (0, 200, 255)  # Blue for laser
        
        pygame.draw.rect(surface, fill_color, (ammo_bar_x, ammo_bar_y, ammo_fill_width, ammo_bar_height))
    
    # Border
    pygame.draw.rect(surface, (200, 200, 200), (ammo_bar_x, ammo_bar_y, ammo_bar_width, ammo_bar_height), 1)
    
    # Reload indicator
    if is_reloading:
        reload_text = small_font.render("RELOADING...", True, (255, 100, 100))
        surface.blit(reload_text, (panel_x + 10, panel_y + 85))
        
        # Reload progress bar
        reload_progress = 1.0 - (reload_time / 2.0)
        reload_bar_width = ammo_bar_width * reload_progress
        pygame.draw.rect(surface, (255, 50, 50), (ammo_bar_x, ammo_bar_y, reload_bar_width, 3))

def enter_level_2():
    """Warp player to Level-2 Rooftop Hideout, reset game state for level 2."""
    global current_room, player, health, max_health, weapon_level, armor_level
    global has_weapon, ammo, max_ammo, inventory, quests
    global collected_gold, collected_herbs, collected_potions, collected_keys, collected_timeshards
    global boss_defeated, boss_drop_collected
    
    try:
        # move player to Factory Exterior in Level 2
        current_room[0] = 1
        current_room[1] = 1
        current_room[2] = 2
        # place player at the Factory Exterior spawn point
        # use a moderately right-of-center spawn so player faces the area
        player.center = (ROOM_WIDTH // 2 + 150, ROOM_HEIGHT // 2)
       
        health = 100
        max_health = 100
        
        has_weapon = False  
        ammo = 0
        max_ammo = 40  
        weapon_level = 1

        keep_gold = inventory.get("Gold", 0)
        inventory = {
            "Gold": keep_gold,
            "Health Potions": 1,  
            "Herbs": 0,
            "Keys": 0,
            "Time Shards": 0
        }
        
        collected_gold.clear()
        collected_herbs.clear()
        collected_potions.clear()
        collected_keys.clear()
        collected_timeshards.clear()
        
        boss_defeated = False
        boss_drop_collected = False

        quests.clear()
        quests.update({
            "explore_neon_city": {"active": True, "complete": False, "description": "Explore the Neon City"},
            "buy_laser_weapon": {"active": True, "complete": False, "description": "Buy a laser weapon from the Neon Market (50 Credits)"},
            "upgrade_laser": {"active": False, "complete": False, "description": "Upgrade your laser weapon"},
            "upgrade_energy_shield": {"active": False, "complete": False, "description": "Upgrade your energy shield"},
            "defeat_cyber_boss": {"active": False, "complete": False, "description": "Defeat the Cyber Security AI"},
            "find_shard_2": {"active": False, "complete": False, "description": "Find Second Time Shard"},
        })
        
        set_message("Welcome to Level 2 – The Neon City! Good luck!", (0, 255, 255), 5.0)
    except Exception:
        tb = traceback.format_exc()
        print("Error entering level 2:\n", tb)
        set_message("Error entering level 2 (see console).", (255, 0, 0), 5.0)
def update_thrown_axes(dt_sec):
    """Update positions of thrown axes and check for collisions."""
    global boss_thrown_axes, health
    
    axes_to_remove = []
    
    for i, axe in enumerate(boss_thrown_axes):
       
        axe["x"] += axe["dx"] * dt_sec
        axe["y"] += axe["dy"] * dt_sec
        axe["angle"] += 10  
        
        
        if (axe["x"] < -50 or axe["x"] > ROOM_WIDTH + 50 or 
            axe["y"] < -50 or axe["y"] > ROOM_HEIGHT + 50):
            axes_to_remove.append(i)
            continue
        
        
        axe_rect = pygame.Rect(axe["x"] - 20, axe["y"] - 10, 40, 20)
        if player.colliderect(axe_rect):
            # thrown axes deal up to boss_axe_damage (reduced by armor)
            damage = boss_axe_damage - (armor_level * 3)
            health = max(0, health - damage)
            set_message(f"Thrown axe hit for {damage} damage!", (255, 0, 0), 1.5)
            axes_to_remove.append(i)
    
   
    for i in sorted(axes_to_remove, reverse=True):
        boss_thrown_axes.pop(i)

def calculate_axe_rect():
    """Calculate the current position of the boss's axe."""
    if not boss:
        return pygame.Rect(0, 0, 0, 0)
    
    center_x = boss["rect"].centerx
    center_y = boss["rect"].centery
    
    radius = 90  
    angle_rad = math.radians(boss_axe_angle)
    
    if boss["last_direction"] == "right":
        axe_x = center_x + radius * math.cos(angle_rad)
        axe_y = center_y + radius * math.sin(angle_rad)
    else:
        axe_x = center_x - radius * math.cos(angle_rad)
        axe_y = center_y + radius * math.sin(angle_rad)
    
    return pygame.Rect(axe_x - 40, axe_y - 20, 80, 40)

def draw_boss(surface):
    """Draw the boss and his axe."""
    if not boss or not boss["alive"]:
        return
    
    img = load_npc_image("boss1")
    surface.blit(img, (boss["rect"].x, boss["rect"].y))
    
    if boss_axe_swinging:
        axe_rect = calculate_axe_rect()
        axe_img = load_axe_image()
        
        rotated_axe = pygame.transform.rotate(axe_img, -boss_axe_angle)
        if boss["last_direction"] == "left":
            rotated_axe = pygame.transform.flip(rotated_axe, True, False)
        
        surface.blit(rotated_axe, (axe_rect.x, axe_rect.y))
    
    
    for axe in boss_thrown_axes:
        axe_img = load_axe_image()
        rotated_axe = pygame.transform.rotate(axe_img, -axe["angle"])
        surface.blit(rotated_axe, (axe["x"] - 40, axe["y"] - 20))
    
    
    health_width = 300
    health_x = ROOM_WIDTH // 2 - health_width // 2
    health_y = 20
    
    pygame.draw.rect(surface, (100, 0, 0), (health_x, health_y, health_width, 25))
    pygame.draw.rect(surface, (255, 0, 0), (health_x, health_y, health_width * (boss_health / boss_max_health), 25))
    pygame.draw.rect(surface, (255, 255, 255), (health_x, health_y, health_width, 25), 2)
    
    phase_text = f"Goblin King (Phase {boss_phase}): {int(boss_health)}/{boss_max_health}"
    health_text = font.render(phase_text, True, (255, 255, 255))
    surface.blit(health_text, (health_x + 5, health_y + 3))

def check_boss_hit():
    """Check if bullets hit the boss."""
    global boss_health, bullets, boss_defeated, boss_phase
    
    if not boss or not boss["alive"]:
        return
    
    bullets_to_remove = []
    for i, bullet in enumerate(bullets):
        bullet_rect = pygame.Rect(bullet["x"] - 2, bullet["y"] - 2, 4, 4)
        if boss["rect"].colliderect(bullet_rect):
            boss_health -= bullet["damage"]
            bullets_to_remove.append(i)
            
            
            if boss_phase == 1 and boss_health <= boss_max_health // 2:
                boss_phase = 2
                boss_health = boss_max_health // 2  
                set_message("The Goblin King enters Phase 2! He's faster and throws axes!", (255, 100, 100), 3.0)
            
            if boss_health <= 0:
                boss["alive"] = False
                boss_defeated = True
                set_message("Goblin King defeated! Collect the drops!", (0, 255, 0), 3.0)
    
    
    for i in sorted(bullets_to_remove, reverse=True):
        bullets.pop(i)

def draw_boss_drops(surface):
    """Draw the boss drops after defeat."""
    if boss_defeated and not boss_drop_collected:
       
        timeshard_img = load_item_image("timeshard")
        surface.blit(timeshard_img, (boss["rect"].centerx - 25, boss["rect"].centery - 25))
        
       
        key_img = load_item_image("key")
        surface.blit(key_img, (boss["rect"].centerx + 15, boss["rect"].centery - 25))

def collect_boss_drops():
    """Collect boss drops when player walks over them."""
    global boss_drop_collected, inventory, quests
    
    if boss_defeated and not boss_drop_collected:
        drop_rect = pygame.Rect(boss["rect"].centerx - 40, boss["rect"].centery - 40, 80, 80)
        if player.colliderect(drop_rect):
            inventory["Time Shards"] += 1
            inventory["Keys"] += 1
            boss_drop_collected = True
            quests["defeat_goblin_king"]["complete"] = True
            quests["find_shard_1"]["complete"] = True
            set_message("Collected Time Shard and Key from Goblin King!", (0, 255, 0), 3.0)

# ------------------ SECOND BOSS (AI Control Room) ------------------
boss2 = None
boss2_health = 0
boss2_max_health = 0
boss2_alive = False
boss2_defeated = False
boss2_phase = 1  # Phase 1: 300 HP, Phase 2: 450 HP (activated at 150 HP)
boss2_phase1_hp = 3000
boss2_phase2_hp = 6000  # Phase 2: doubled HP
boss2_laser_cooldown = 0.0
boss2_laser_charge_index = 0  # 0-2 for three charges
boss2_lasers = []  # List of active laser beams
boss2_contact_cooldown = 0.0  # Cooldown between contact damage hits (3 seconds)
boss2_projectiles = []  # Boss projectiles
boss2_attack_cooldown = 0.0  # Cooldown between attack cycles
boss2_accuracy = 0.75  # 75% accuracy in phase 1, 80% in phase 2

def init_boss2():
    """Initialize the AI boss in the AI Control Room."""
    global boss2, boss2_health, boss2_max_health, boss2_alive, boss2_defeated, boss2_phase, boss2_laser_cooldown, boss2_laser_charge_index, boss2_lasers, boss2_contact_cooldown, boss2_projectiles, boss2_attack_cooldown, boss2_accuracy
    # place boss2 below and to the right of the player's spawn when entering level 2
    try:
        px, py = player.centerx, player.centery
    except Exception:
        px, py = ROOM_WIDTH // 2, ROOM_HEIGHT // 2
    offset_x, offset_y = 80, 80
    bx = max(0, min(ROOM_WIDTH - 110, int(px + offset_x)))
    by = max(0, min(ROOM_HEIGHT - 130, int(py + offset_y)))
    boss2 = {"rect": pygame.Rect(bx, by, 110, 130), "alive": True}
    boss2_phase = 1
    boss2_max_health = boss2_phase1_hp + boss2_phase2_hp  # Total: 750 HP (300 phase 1, 450 phase 2)
    boss2_health = boss2_phase1_hp  # Start with phase 1 HP
    boss2_alive = True
    boss2_defeated = False
    boss2_laser_cooldown = 0.0
    boss2_laser_charge_index = 0
    boss2_lasers = []
    boss2_contact_cooldown = 0.0
    boss2_projectiles = []
    boss2_attack_cooldown = 0.0
    boss2_accuracy = 0.45  # Phase 1: 45% accuracy

def update_boss2(dt):
    """Boss2 behavior: Phase 1 chases player, Phase 2 (at 150 HP) charges and fires lasers."""
    global boss2_health, boss2_alive, health, boss2_defeated, boss2_phase, boss2_laser_cooldown, boss2_laser_charge_index, boss2_lasers, boss2_contact_cooldown, boss2_projectiles, boss2_attack_cooldown, boss2_accuracy
    if not boss2 or not boss2.get("alive", False):
        return
    
    dt_sec = dt / 1000.0
    boss2_contact_cooldown -= dt_sec
    
    # Check phase transition: enter phase 2 when health drops to 150 HP or below
    if boss2_phase == 1 and boss2_health <= boss2_phase1_hp / 2:
        boss2_phase = 2
        boss2_accuracy = 0.80  # Phase 2: 80% accuracy
        set_message("Phase 2: Boss goes berserk!", (255, 100, 0), 2.0)
    
    # Phase 1: Simple chase (120 speed)
    if boss2_phase == 1:
        dx = player.centerx - boss2["rect"].centerx
        dy = player.centery - boss2["rect"].centery
        dist = math.hypot(dx, dy)
        if dist > 0 and dist < 500:
            step = 120 * dt_sec
            boss2["rect"].x += (dx / dist) * step
            boss2["rect"].y += (dy / dist) * step
        # Phase 1: Fire projectiles at player with 45% accuracy
        if boss2_attack_cooldown <= 0 and dist < 500:
            if random.random() < boss2_accuracy:
                # Fire projectile at player
                proj_dx = player.centerx - boss2["rect"].centerx
                proj_dy = player.centery - boss2["rect"].centery
                proj_dist = math.hypot(proj_dx, proj_dy)
                if proj_dist > 0:
                    # Normalize and scale to projectile speed (similar to player bullets)
                    proj_speed = 300  # pixels per second
                    proj_vx = (proj_dx / proj_dist) * proj_speed
                    proj_vy = (proj_dy / proj_dist) * proj_speed
                    boss2_projectiles.append({
                        "x": boss2["rect"].centerx,
                        "y": boss2["rect"].centery,
                        "vx": proj_vx,
                        "vy": proj_vy,
                        "lifetime": 5.0
                    })
            boss2_attack_cooldown = 0.25  # Fire every 0.25 seconds
    
    # Phase 2: Increased speed (180), charging and laser attacks
    elif boss2_phase == 2:
        dx = player.centerx - boss2["rect"].centerx
        dy = player.centery - boss2["rect"].centery
        dist = math.hypot(dx, dy)
        if dist > 0 and dist < 500:
            step = 180 * dt_sec  # 1.5x base speed
            boss2["rect"].x += (dx / dist) * step
            boss2["rect"].y += (dy / dist) * step
        # Phase 2: Fire projectiles with 50% accuracy
        if boss2_attack_cooldown <= 0 and dist < 500:
            if random.random() < boss2_accuracy:
                # Fire projectile at player
                proj_dx = player.centerx - boss2["rect"].centerx
                proj_dy = player.centery - boss2["rect"].centery
                proj_dist = math.hypot(proj_dx, proj_dy)
                if proj_dist > 0:
                    # Normalize and scale to projectile speed
                    proj_speed = 300  # pixels per second
                    proj_vx = (proj_dx / proj_dist) * proj_speed
                    proj_vy = (proj_dy / proj_dist) * proj_speed
                    boss2_projectiles.append({
                        "x": boss2["rect"].centerx,
                        "y": boss2["rect"].centery,
                        "vx": proj_vx,
                        "vy": proj_vy,
                        "lifetime": 5.0
                    })
            boss2_attack_cooldown = 0.25  # Fire every 0.25 seconds
        
        # Laser charging and firing: 10 second cycle
        boss2_laser_cooldown += dt_sec
        
        # Charge phase: 4 seconds (show charges at target locations)
        if boss2_laser_cooldown < 4.0:
            # Calculate charge locations once (cached in boss2)
            if not boss2.get("charge_locations"):
                # 1 at player, 2 random locations
                boss2["charge_locations"] = [
                    (player.centerx, player.centery),  # Charge 0: at player
                    (random.randint(50, ROOM_WIDTH - 50), random.randint(50, ROOM_HEIGHT - 50)),  # Charge 1: random
                    (random.randint(50, ROOM_WIDTH - 50), random.randint(50, ROOM_HEIGHT - 50))   # Charge 2: random
                ]
            boss2_laser_charge_index = 3  # All 3 charges showing
        
        # Fire phase: 1 second (show lasers at same locations, deal damage)
        elif boss2_laser_cooldown < 5.0:
            # Fire lasers at the charge locations
            if not boss2.get("lasers_fired"):
                charge_locs = boss2.get("charge_locations", [])
                for i, (cx, cy) in enumerate(charge_locs):
                    boss2_lasers.append({
                        "x": cx,
                        "y": cy,
                        "lifetime": 1.0,  # Lasers visible for 1 second
                        "type": "stationary"
                    })
                boss2["lasers_fired"] = True
            boss2_laser_charge_index = 0  # Charges disappear, lasers show
        
        # Reset cycle after 5 seconds (4 charge + 1 laser)
        if boss2_laser_cooldown >= 5.0:
            boss2_laser_cooldown = 0.0
            boss2_laser_charge_index = 0
            boss2["charge_locations"] = None
            boss2["lasers_fired"] = False
    
    # Decrement attack cooldown
    boss2_attack_cooldown -= dt_sec
    
    # Update projectiles: move, check collisions, and remove after lifetime
    projectiles_to_remove = []
    for i, proj in enumerate(boss2_projectiles):
        proj["x"] += proj["vx"] * dt_sec
        proj["y"] += proj["vy"] * dt_sec
        proj["lifetime"] -= dt_sec
        
        # Check if projectile hits player
        if proj["lifetime"] > 0:
            proj_rect = pygame.Rect(proj["x"] - 4, proj["y"] - 4, 8, 8)
            if player.colliderect(proj_rect):
                health = max(0, health - 12)  # 12 damage per hit
                global player_electrified_timer
                player_electrified_timer = 2.0  # Electrified for 2 seconds
                set_message("Hit by boss projectile!", (255, 100, 100), 1.0)
                projectiles_to_remove.append(i)
        
        # Remove if lifetime expired or out of bounds
        if proj["lifetime"] <= 0 or proj["x"] < -50 or proj["x"] > ROOM_WIDTH + 50 or proj["y"] < -50 or proj["y"] > ROOM_HEIGHT + 50:
            if i not in projectiles_to_remove:
                projectiles_to_remove.append(i)
    
    for i in sorted(projectiles_to_remove, reverse=True):
        boss2_projectiles.pop(i)
    
    # Update lasers: check collisions and remove after lifetime
    lasers_to_remove = []
    for i, laser in enumerate(boss2_lasers):
        laser["lifetime"] -= dt_sec
        
        # Check if laser hits player (only during active phase)
        if laser["lifetime"] > 0:
            laser_rect = pygame.Rect(laser["x"] - 16, laser["y"] - 16, 32, 32)
            if player.colliderect(laser_rect):
                health = 0  # One-shot the player
                set_message("Hit by laser! Game Over!", (255, 0, 0), 2.0)
        
        # Remove if lifetime expired
        if laser["lifetime"] <= 0:
            lasers_to_remove.append(i)
    
    for i in sorted(lasers_to_remove, reverse=True):
        boss2_lasers.pop(i)

def check_boss2_hit():
    global boss2_health, bullets, boss2_alive, boss2_defeated, boss2_phase
    if not boss2 or not boss2.get("alive", False):
        return
    bullets_to_remove = []
    for i, bullet in enumerate(bullets):
        bullet_rect = pygame.Rect(bullet["x"] - 2, bullet["y"] - 2, 4, 4)
        if boss2["rect"].colliderect(bullet_rect):
            boss2_health -= bullet["damage"]
            bullets_to_remove.append(i)
            if boss2_health <= 0:
                boss2["alive"] = False
                boss2_alive = False
                boss2_defeated = True
                # spawn drops in the AI Control Room
                room_key = (1, 2, 2)
                room_info = room_data.get(room_key, {})
                if room_info is not None:
                    room_info.setdefault("items", []).append({"type": "timeshard", "x": boss2["rect"].centerx - 25, "y": boss2["rect"].centery - 25, "id": "timeshard_ai_1"})
                    room_info.setdefault("items", []).append({"type": "keycard", "x": boss2["rect"].centerx + 15, "y": boss2["rect"].centery - 25, "id": "keycard_ai_1"})
                set_message("AI Core defeated! Drops spawned in the room.", (0, 255, 0), 3.0)
    for i in sorted(bullets_to_remove, reverse=True):
        bullets.pop(i)

def draw_boss2(surface):
    global boss2_phase, boss2_laser_charge_index, boss2_lasers
    if not boss2 or not boss2.get("alive", False):
        return
    img = load_npc_image("boss2")
    surface.blit(img, (boss2["rect"].x, boss2["rect"].y))
    
    # Draw charge indicators in phase 2 (charge.png at target locations)
    if boss2_phase == 2 and boss2_laser_charge_index == 3:
        charge_locs = boss2.get("charge_locations", [])
        for cx, cy in charge_locs:
            try:
                charge_img = load_image("objects/charge.png", 64, 64)
                surface.blit(charge_img, (cx - 32, cy - 32))
            except:
                # Fallback: yellow circle if charge.png not found
                pygame.draw.circle(surface, (255, 255, 0), (int(cx), int(cy)), 16)
    
    # Draw lasers as blue dots (like bullet coins)
    for laser in boss2_lasers:
        if laser["lifetime"] > 0:
            # Draw blue laser dot similar to bullet coins
            color_main = (0, 150, 255)
            color_inner = (100, 200, 255)
            pygame.draw.circle(surface, color_main, (int(laser["x"]), int(laser["y"])), 12)
            pygame.draw.circle(surface, color_inner, (int(laser["x"]), int(laser["y"])), 9)
            pygame.draw.circle(surface, (50, 100, 200), (int(laser["x"]), int(laser["y"])), 6)
    
    # Draw boss2 projectiles as blue balls (like player bullets)
    for proj in boss2_projectiles:
        if proj["lifetime"] > 0:
            # Draw blue projectile (same style as player bullets)
            color_main = (0, 150, 255)  # Blue
            color_inner = (100, 200, 255)
            color_edge = (50, 100, 200)
            pygame.draw.circle(surface, color_main, (int(proj["x"]), int(proj["y"])), 6)
            pygame.draw.circle(surface, color_inner, (int(proj["x"]), int(proj["y"])), 4)
            pygame.draw.circle(surface, color_edge, (int(proj["x"]), int(proj["y"])), 2)
    
    # health bar
    health_width = 250
    health_x = ROOM_WIDTH // 2 - health_width // 2
    health_y = 20
    pygame.draw.rect(surface, (100, 0, 0), (health_x, health_y, health_width, 20))
    pygame.draw.rect(surface, (255, 0, 0), (health_x, health_y, health_width * (boss2_health / boss2_max_health), 20))
    pygame.draw.rect(surface, (255, 255, 255), (health_x, health_y, health_width, 20), 2)
    
    # Phase indicator
    phase_text = f"Phase {boss2_phase}"
    phase_surf = small_font.render(phase_text, True, (255, 255, 0) if boss2_phase == 2 else (255, 255, 255))
    surface.blit(phase_surf, (health_x + health_width + 10, health_y))


#  weapon and shooting system
def shoot_bullet():
    global ammo, shoot_cooldown, is_reloading, is_laser_weapon
    
    if not has_weapon:
        set_message("You need a weapon! Visit the blacksmith.", (255, 200, 0), 2.0)
        return False
    
    current_cooldown = LASER_COOLDOWN_TIME if is_laser_weapon else REGULAR_COOLDOWN_TIME
        
    if not is_reloading and ammo > 0 and shoot_cooldown <= 0:
        dx = mouse_x - player.centerx
        dy = mouse_y - player.centery
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0:
            bullet_speed = 20.0 if is_laser_weapon else 15.0
            damage = 20 + (weapon_level * 5)  
            if is_laser_weapon:
                damage += 15
            
            if is_laser_weapon:
                bullet_color_main = (0, 255, 255)
                bullet_color_inner = (0, 200, 255)
                bullet_radius = 6
            else:
                bullet_color_main = (255, 255, 0)
                bullet_color_inner = (255, 200, 0)
                bullet_radius = 4
            
            bullets.append({
                "x": float(player.centerx),
                "y": float(player.centery),
                "dx": (dx / dist) * bullet_speed,
                "dy": (dy / dist) * bullet_speed,
                "damage": damage,
                "is_laser": is_laser_weapon,
                "color_main": bullet_color_main,
                "color_inner": bullet_color_inner,
                "radius": bullet_radius
            })
            
            ammo -= 1
            shoot_cooldown = current_cooldown
            
            # level-based gunshot audio: medieval (level 0) uses gunshot, cyber (level 1) uses laser
            level_id = current_room[0] if current_room else 0
            if level_id == 1:
                play_sound(LASER_SOUND)
            else:
                play_sound(GUNSHOT_SOUND)
            
            if is_laser_weapon:
                set_message("Pew! Laser!", (0, 255, 255), 0.3)
            else:
                set_message("Pew!", (255, 255, 0), 0.5)
                
            return True


    if ammo == 0 and has_weapon and not is_reloading:
        if is_laser_weapon:
            set_message("Energy cells depleted! Buy more from Neon Market.", (255, 100, 255), 1.5)
        else:
            set_message("Out of ammo! Buy more from the blacksmith.", (255, 200, 0), 1.5)
    
    return False

def update_bullets(dt):
    """Update bullet positions and check collisions."""
    global bullets
    
    bullets_to_remove = []
    for i, bullet in enumerate(bullets):
        bullet["x"] += bullet["dx"] * (dt / 16.0)
        bullet["y"] += bullet["dy"] * (dt / 16.0)
        
       
        if (bullet["x"] < 0 or bullet["x"] > ROOM_WIDTH or 
            bullet["y"] < 0 or bullet["y"] > ROOM_HEIGHT):
            bullets_to_remove.append(i)
            continue

       
        room_key = tuple(current_room)
        state = goblin_rooms.get(room_key)
        if state:
            w, h = get_npc_size("goblin")
            for goblin in state["active"]:
                if not goblin.get("alive", True):
                    continue
                goblin_rect = pygame.Rect(goblin["x"], goblin["y"], w, h)
                if goblin_rect.collidepoint(bullet["x"], bullet["y"]):
                    goblin["alive"] = False
                    if not goblin.get("loot_given"):
                        
                        inventory["Gold"] += 10
                        goblin["loot_given"] = True
                        message_text = "+10 Gold (Goblin)"
                        set_message(message_text, (255, 215, 0), 1.5)
                    bullets_to_remove.append(i)
                    break
        # check time bandits as well
        tb_state = timebandit_rooms.get(room_key)
        if tb_state:
            default_w, default_h = get_npc_size("timebandit")
            for tb in tb_state["active"]:
                if not tb.get("alive", True):
                    continue
                w = int(tb.get("w", default_w))
                h = int(tb.get("h", default_h))
                tb_rect = pygame.Rect(tb["x"], tb["y"], w, h)
                if tb_rect.collidepoint(bullet["x"], bullet["y"]):
                    # If the timebandit has HP (miniboss), subtract; otherwise kill in one hit
                    if tb.get("hp") is not None:
                        tb["hp"] -= bullet.get("damage", 0)
                        bullets_to_remove.append(i)
                        if tb["hp"] <= 0:
                            tb["alive"] = False
                            if not tb.get("loot_given"):
                                # miniboss does NOT drop a keycard on death (per design)
                                inventory["Gold"] += 150
                                tb["loot_given"] = True
                                set_message("Miniboss defeated!", (255, 215, 0), 2.5)
                        # miniboss takes multiple hits; don't give normal bandit gold here
                    else:
                        tb["alive"] = False
                        if not tb.get("loot_given"):
                            inventory["Gold"] += 15
                            tb["loot_given"] = True
                            set_message("+15 Gold (Time Bandit)", (255, 215, 0), 1.5)
                        bullets_to_remove.append(i)
                    break

            # If all waves finished and none active, spawn a keycard in this room once
            if not any(tb.get("alive", True) for tb in tb_state["active"]) and tb_state["wave_index"] >= len(tb_state["waves"]) and not tb_state.get("key_given"):
                room_info = room_data.get(room_key, {})
                items = room_info.get("items")
                if items is not None:
                    items.append({"type": "keycard", "x": ROOM_WIDTH//2 - 20, "y": ROOM_HEIGHT//2 - 20, "id": f"keycard_timebandit_{room_key[1]}_{room_key[2]}"})
                    # Reward player for clearing the time bandits
                    try:
                        inventory["Gold"] += 50
                        set_message("+50 Gold (Time Bandits cleared)", (255, 215, 0), 2.5)
                    except Exception:
                        pass
                tb_state["key_given"] = True
                set_message("A Keycard has appeared!", (255, 215, 0), 3.0)
    
   
    if tuple(current_room) == (0, 2, 0) and boss and boss["alive"]:
        check_boss_hit()
    if tuple(current_room) == (1, 2, 2) and boss2 and boss2.get("alive", False):
        check_boss2_hit()
    

    for i in sorted(bullets_to_remove, reverse=True):
        bullets.pop(i)

def draw_bullets(surface):
    
    for bullet in bullets:
        color_main = bullet.get("color_main", (255, 255, 0))
        color_inner = bullet.get("color_inner", (255, 200, 0))
        radius = bullet.get("radius", 4)
        
        pygame.draw.circle(surface, color_main, (int(bullet["x"]), int(bullet["y"])), radius)
        pygame.draw.circle(surface, color_inner, (int(bullet["x"]), int(bullet["y"])), radius-2)
        
        if bullet.get("is_laser", False):
            trail_length = 15
            for i in range(1, 4):
                trail_x = bullet["x"] - bullet["dx"] * (i * 0.3)
                trail_y = bullet["y"] - bullet["dy"] * (i * 0.3)
                trail_alpha = 150 - (i * 50)
                trail_color = (0, 200, 255, trail_alpha)
                
                trail_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.draw.circle(trail_surf, trail_color, (radius, radius), max(1, radius-i))
                surface.blit(trail_surf, (int(trail_x)-radius, int(trail_y)-radius))

def draw_weapon_hud(surface):
    """Draw weapon ammo and reload status."""
    if has_weapon:
        ammo_text = font.render(f"Ammo: {ammo}/{max_ammo}", True, (255, 255, 255))
        surface.blit(ammo_text, (10, 10))
        
        if is_reloading:
            reload_text = font.render("RELOADING...", True, (255, 0, 0))
            surface.blit(reload_text, (10, 40))
        elif ammo == 0:
            reload_hint = font.render("Buy ammo from Blacksmith", True, (255, 200, 0))
            surface.blit(reload_hint, (10, 40))
        
       
        weapon_text = small_font.render(f"Weapon Lvl: {weapon_level}", True, (200, 200, 255))
        armor_text = small_font.render(f"Armor Lvl: {armor_level}", True, (200, 255, 200))
        surface.blit(weapon_text, (10, ROOM_HEIGHT - 80))
        surface.blit(armor_text, (10, ROOM_HEIGHT - 60))
    else:
        
        no_weapon_text = font.render("No Weapon - Visit Blacksmith", True, (255, 100, 100))
        surface.blit(no_weapon_text, (10, 10))
        hint_text = small_font.render("", True, (200, 200, 200))
        surface.blit(hint_text, (10, 40))
        
        
        if armor_level > 0:
            armor_text = small_font.render(f"Armor Lvl: {armor_level}", True, (200, 255, 200))
            surface.blit(armor_text, (10, ROOM_HEIGHT - 60))

def draw_cyber_shop(surface):
    """Draw the cyberpunk shop interface."""
    if not cyber_shop_visible:
        return
    
    overlay = pygame.Surface((ROOM_WIDTH, ROOM_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    surface.blit(overlay, (0, 0))
    
    # Main shop window
    shop_rect = pygame.Rect(50, 50, ROOM_WIDTH - 100, ROOM_HEIGHT - 100)
    pygame.draw.rect(surface, (10, 10, 30), shop_rect)
    pygame.draw.rect(surface, (0, 255, 255), shop_rect, 4)
    
    # Title
    title = title_font.render("NEON MARKET", True, (0, 255, 255))
    surface.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, 70))
    
    # Gold display
    gold_rect = pygame.Rect(shop_rect.x + 20, shop_rect.y + 80, shop_rect.width - 40, 40)
    pygame.draw.rect(surface, (20, 20, 40), gold_rect)
    pygame.draw.rect(surface, (255, 215, 0), gold_rect, 2)
    
    gold_text = font.render(f"Credits: {inventory['Gold']}", True, (255, 215, 0))
    surface.blit(gold_text, (gold_rect.centerx - gold_text.get_width()//2, gold_rect.centery - gold_text.get_height()//2))
    
    # Player stats
    stats_rect = pygame.Rect(shop_rect.x + 20, shop_rect.y + 130, shop_rect.width - 40, 60)
    pygame.draw.rect(surface, (20, 30, 50), stats_rect)
    pygame.draw.rect(surface, (100, 150, 255), stats_rect, 2)
    
    cyber_damage = 15 if blacksmith_items['cyber_weapon']['purchased'] else 0
    cyber_health = 50 if blacksmith_items['cyber_armor']['purchased'] else 0
    cyber_ammo_cap = 50 if blacksmith_items['cyber_weapon']['purchased'] else 0
    
    stats_lines = [
        f"Weapon Damage: {20 + (weapon_level * 5) + cyber_damage}",
        f"Max Health: {max_health + cyber_health} | Current: {health}",
        f"Ammo: {ammo}/{max_ammo + cyber_ammo_cap}",
        f"Ammo Packs bought (this level): {ammo_packs_bought.get(current_room[0],0)}/{MAX_AMMO_PACKS}"
    ]
    
    for i, line in enumerate(stats_lines):
        stat_text = small_font.render(line, True, (180, 220, 255))
        surface.blit(stat_text, (stats_rect.x + 10, stats_rect.y + 5 + i * 20))
    
    # Shop items
    items_rect = pygame.Rect(shop_rect.x + 20, shop_rect.y + 210, shop_rect.width - 40, shop_rect.height - 280)
    pygame.draw.rect(surface, (30, 30, 60), items_rect)
    pygame.draw.rect(surface, (0, 150, 200), items_rect, 2)
    
    # Cyber items
    cyber_items = [
        ("cyber_weapon", "Neon Blaster", "High-tech firearm", 50, "+15 Damage, +50 Ammo Cap"),
        ("cyber_armor", "Energy Shield", "Advanced armor", 40, "+50 Max Health"),
        ("cyber_ammo", "Energy Cells", "Ammo pack", 20, "+50 Ammo"),
        ("cyber_potion", "Nanite Heal", "Advanced healing", 25, "+50 Health")
    ]
    
    item_buttons = []
    for i, (item_id, name, desc, cost, bonus) in enumerate(cyber_items):
        row = i // 2
        col = i % 2
        item_x = items_rect.x + 20 + col * (items_rect.width // 2)
        item_y = items_rect.y + 20 + row * 120
        
        item_bg = pygame.Rect(item_x, item_y, items_rect.width // 2 - 30, 110)
        
        item = blacksmith_items[item_id]
        if item.get("purchased", False):
            bg_color = (0, 40, 40)
            border_color = (0, 200, 200)
        elif inventory["Gold"] >= cost:
            bg_color = (30, 30, 50)
            border_color = (0, 150, 200)
        else:
            bg_color = (40, 30, 40)
            border_color = (200, 0, 100)
        
        pygame.draw.rect(surface, bg_color, item_bg)
        pygame.draw.rect(surface, border_color, item_bg, 3)
        
        # Item info
        name_text = font.render(name, True, (255, 255, 255))
        desc_text = small_font.render(desc, True, (200, 200, 255))
        cost_text = font.render(f"{cost} Cr", True, (255, 215, 0))
        bonus_text = small_font.render(bonus, True, (0, 255, 150))
        
        surface.blit(name_text, (item_bg.x + 10, item_bg.y + 10))
        surface.blit(desc_text, (item_bg.x + 10, item_bg.y + 35))
        surface.blit(cost_text, (item_bg.x + item_bg.width - 80, item_bg.y + 10))
        surface.blit(bonus_text, (item_bg.x + 10, item_bg.y + 55))
        
        # Purchase button
        if not item.get("purchased", False):
            button_rect = pygame.Rect(item_bg.x + item_bg.width - 90, item_bg.y + 70, 80, 30)
            # Determine if player can purchase this cyber item (consider per-level ammo limits)
            can_purchase = inventory["Gold"] >= cost and (item_id != "cyber_ammo" or ammo_packs_bought.get(current_room[0], 0) < MAX_AMMO_PACKS)
            if can_purchase:
                pygame.draw.rect(surface, (0, 80, 80), button_rect)
                pygame.draw.rect(surface, (0, 200, 200), button_rect, 2)
                button_text = small_font.render("BUY", True, (200, 255, 255))
            else:
                pygame.draw.rect(surface, (80, 0, 0), button_rect)
                pygame.draw.rect(surface, (200, 0, 100), button_rect, 2)
                button_text = small_font.render("BUY", True, (255, 200, 200))
            
            surface.blit(button_text, (button_rect.centerx - button_text.get_width()//2, button_rect.centery - button_text.get_height()//2))
            item_buttons.append((button_rect, item_id))
        else:
            owned_text = font.render("OWNED", True, (0, 255, 0))
            surface.blit(owned_text, (item_bg.x + item_bg.width - 90, item_bg.y + 70))
    
    # Close button
    close_rect = pygame.Rect(shop_rect.centerx - 60, shop_rect.bottom - 50, 120, 40)
    pygame.draw.rect(surface, (100, 0, 100), close_rect)
    pygame.draw.rect(surface, (255, 0, 255), close_rect, 3)
    close_text = font.render("EXIT", True, (255, 255, 255))
    surface.blit(close_text, (close_rect.centerx - close_text.get_width()//2, close_rect.centery - close_text.get_height()//2))
    
    return item_buttons, close_rect
def handle_cyber_purchase(item_id):
    global ammo, max_ammo, health, max_health, inventory, weapon_level, has_weapon, is_laser_weapon
    
    item = blacksmith_items[item_id]
    
    if item.get("purchased", False):
        set_message(f"You already own {item['name']}!", (255, 200, 0), 2.0)
        return False
    
    if inventory["Gold"] < item["cost"]:
        set_message(f"Not enough credits for {item['name']}!", (255, 0, 0), 2.0)
        return False

    # Prevent buying more than allowed ammo packs per level
    elif item_id == "cyber_ammo":
        pack_amount = 50
        ammo_packs_bought[level] = ammo_packs_bought.get(level, 0) + 1
        inventory["Ammo Packs"] = inventory.get("Ammo Packs", 0) + 1
        set_message(f"Purchased {item['name']} ({ammo_packs_bought[level]}/{MAX_AMMO_PACKS})! Ammo Packs: {inventory['Ammo Packs']}", (0, 255, 255), 2.0)
    # Deduct cost and apply effects per item. Only mark persistent items as purchased.
    inventory["Gold"] -= item["cost"]
    
    if item_id == "cyber_weapon":
        has_weapon = True
        is_laser_weapon = True
        max_ammo += 50
        ammo = max_ammo
        weapon_level += 1
        quests["buy_laser_weapon"]["complete"] = True
        quests["upgrade_laser"]["active"] = True
        item["purchased"] = True
        set_message(f"Purchased {item['name']}! +15 Damage, +50 Ammo, Faster Fire Rate!", (0, 255, 255), 3.0)
    
    elif item_id == "cyber_armor":
        max_health += 50
        health = max_health
        quests["upgrade_energy_shield"]["active"] = True
        item["purchased"] = True
        set_message(f"Purchased {item['name']}! +50 Max Health", (0, 255, 255), 3.0)
    
    elif item_id == "cyber_ammo":
        # Consumable: increment per-level counter and add ammo (50 per pack)
        level = current_room[0]
        pack_amount = 50
        ammo_packs_bought[level] = ammo_packs_bought.get(level, 0) + 1
        ammo = min(max_ammo, ammo + pack_amount)
        inventory["Ammo"] = inventory.get("Ammo", 0) + pack_amount
        set_message(f"Purchased {item['name']} ({ammo_packs_bought[level]}/{MAX_AMMO_PACKS})! +{pack_amount} Energy Cells", (0, 255, 255), 2.0)
    
    elif item_id == "cyber_potion":
        health = min(max_health, health + 50)
        set_message(f"Used {item['name']}! +50 Health", (0, 255, 255), 2.0)
    
    return True
def respawn_player():
    """Handle player respawn with penalties."""
    global health, max_health, weapon_level, armor_level, player, current_room, ammo, is_reloading, reload_time
    
   
    if weapon_level > 1:
        weapon_level -= 1
    if armor_level > 0:
        armor_level -= 1
        max_health = 100 + (armor_level * 20)  
    
    
    health = max_health
    player.x = 100
    player.y = ROOM_HEIGHT - 150
    current_room = [0, 0, 0]  
    ammo = 0 if not has_weapon else max_ammo
    is_reloading = False
    reload_time = 0.0
    
    set_message("You died! Respawned in village. Lost 1 weapon and armor level.", (255, 100, 100), 4.0)

#  drawing zones 
def draw_object(x, y, obj_type, surface, level, width=None, height=None):
    """Draw objects using images only."""
    # For invisible barriers
    if obj_type == "invisible":
        rect = pygame.Rect(x, y, width, height)
        colliders.append(rect)
        
        # Draw invisible barriers in development mode only
        if DEV_MODE:
           
            debug_surface = pygame.Surface((width, height), pygame.SRCALPHA)
           
            debug_surface.fill((255, 0, 0, 80))  # Semi-transparent red
            surface.blit(debug_surface, (x, y))
           
            pygame.draw.rect(surface, (255, 0, 0), (x, y, width, height), 2)
       
            label_font = pygame.font.SysFont(None, 20)
            label = label_font.render("INVISIBLE", True, (255, 255, 255))
            surface.blit(label, (x + 5, y + 5))
        
        return rect
    
    
    if obj_type == "damage":
        rect = pygame.Rect(x, y, width, height)
        damage_zones.append(rect)
        
        
        if DEV_MODE:
            debug_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            debug_surface.fill((255, 100, 0, 60))  
            surface.blit(debug_surface, (x, y))
            pygame.draw.rect(surface, (255, 100, 0), (x, y, width, height), 2)
           
            label_font = pygame.font.SysFont(None, 20)
            label = label_font.render("DAMAGE", True, (255, 255, 255))
            surface.blit(label, (x + 5, y + 5))
        
        return rect
    elif obj_type == "shop":
        img = load_object_image("shop", width, height)
        if img:
            surface.blit(img, (x, y))
        
        rect = pygame.Rect(x, y, width, height)
        interactive_objects.append({"rect": rect, "type": obj_type, "x": x, "y": y})
        return rect    

    img = load_object_image(obj_type, width, height)
    surface.blit(img, (x, y))
    
  
    rect = pygame.Rect(x, y, width, height)
    

    if obj_type in ["tree", "rock", "building", "bridge_wall", "bridge"]:
        colliders.append(rect)
    
    if obj_type in ["anvil", "campfire", "cage", "lever", "portal", "bookshelf", "rune", "safe", "datahub"]:
        interactive_objects.append({"rect": rect, "type": obj_type, "x": x, "y": y})
        if obj_type != "portal":  
            colliders.append(rect)
    
    return rect


def handle_damage_zones(dt):
    """Check if player is in damage zones and apply damage."""
    global health, damage_timer, message, message_timer, message_color
    
    damage_timer += dt / 1000.0  


    player_in_damage_zone = False
    for zone in damage_zones:
        if player.colliderect(zone):
            player_in_damage_zone = True
            break
    
    if player_in_damage_zone:

        if damage_timer >= 1.0:
            damage_timer = 0.0
            health -= 5  
            
            set_message("-5 Health!", (255, 0, 0), 1.0)
            
            if health <= 0:
                health = 0
                respawn_player()
        
 
        pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) * 0.5  
        border_alpha = int(80 + pulse * 80)  
        border_width = int(5 + pulse * 10)  
        

        border_surface = pygame.Surface((ROOM_WIDTH, ROOM_HEIGHT), pygame.SRCALPHA)
        

        pygame.draw.rect(border_surface, (255, 0, 0, border_alpha), (0, 0, ROOM_WIDTH, border_width))

        pygame.draw.rect(border_surface, (255, 0, 0, border_alpha), (0, ROOM_HEIGHT - border_width, ROOM_WIDTH, border_width))

        pygame.draw.rect(border_surface, (255, 0, 0, border_alpha), (0, 0, border_width, ROOM_HEIGHT))
     
        pygame.draw.rect(border_surface, (255, 0, 0, border_alpha), (ROOM_WIDTH - border_width, 0, border_width, ROOM_HEIGHT))
        
        screen.blit(border_surface, (0, 0))
        
    else:
  
        damage_timer = 0.0

def _player_frame_for_state(state, direction):
    """Pick the correct frame list for the given state/direction."""
    _ensure_player_frames()
    key = f"{state}_{direction}"
    frames = player_anim_frames.get(key)
    if frames:
        return frames
    return player_anim_frames.get(f"idle_{direction}", [])

def draw_player(surface, player_rect, dt, moving):
    """Draw player using the new run/idle sprite sheets."""
    global player_anim_state, player_anim_index, player_anim_timer
    
    direction = "left" if player_direction == "left" else "right"
    state = "run" if moving else "idle"
    frames = _player_frame_for_state(state, direction)
    if not frames:
        img = load_player_image(direction)
        img_rect = img.get_rect(center=player_rect.center)
        surface.blit(img, img_rect)
        return
    
    if state != player_anim_state:
        player_anim_state = state
        player_anim_index = 0
        player_anim_timer = 0.0
    
    if moving:
        player_anim_timer += dt / 1000.0
        if player_anim_timer >= PLAYER_ANIM_SPEED:
            player_anim_timer = 0.0
            player_anim_index = (player_anim_index + 1) % len(frames)
    else:
        player_anim_index = 0
        player_anim_timer = 0.0
    
    frame = frames[player_anim_index % len(frames)]
    frame_rect = frame.get_rect(center=player_rect.center)
    surface.blit(frame, frame_rect)

def draw_player_pointer(surface, player_rect):
    """Draw a small pointer anchored to the player's left side."""
    center_y = player_rect.centery
    tip_x = player_rect.left + POINTER_OFFSET_X
    points = [
        (tip_x + POINTER_SIZE, center_y - POINTER_SIZE // 2),
        (tip_x, center_y),
        (tip_x + POINTER_SIZE, center_y + POINTER_SIZE // 2),
    ]
    pygame.draw.polygon(surface, POINTER_COLOR, points)

def draw_npc(surface, x, y, npc_id, rescued=False):
    """Draw NPCs using images."""
    img = load_npc_image(npc_id)
    surface.blit(img, (x, y))
    size = get_npc_size(npc_id)
    rect = pygame.Rect(x, y, size[0], size[1])
    
   
    if not rescued:
        colliders.append(rect)
        npcs.append(rect)
    return rect

def draw_goblins(surface, room_key):
    """Draw goblin enemies for the current room."""
    state = goblin_rooms.get(room_key)
    if not state:
        return
    w, h = get_npc_size("goblin")
    for goblin in state["active"]:
        if not goblin.get("alive", True):
            continue
        img = load_npc_image("goblin")
        surface.blit(img, (goblin["x"], goblin["y"]))
        # Goblins handle their own collision/damage; keep them out of the collider list
        # so they do not push the player back like walls.

def draw_timebandits(surface, room_key):
    """Draw time-bandit enemies for the current room."""
    state = timebandit_rooms.get(room_key)
    if not state:
        return
    default_w, default_h = get_npc_size("timebandit")
    for tb in state["active"]:
        if not tb.get("alive", True):
            continue
        w = int(tb.get("w", default_w))
        h = int(tb.get("h", default_h))
        try:
            img = load_npc_image("timebandit")
            # scale image for minibosses if needed
            if (w, h) != (default_w, default_h):
                img = pygame.transform.scale(img, (w, h))
            surface.blit(img, (tb["x"], tb["y"]))
            # Draw miniboss health bar
            if tb.get("boss"):
                hp = tb.get("hp", 0)
                max_hp = tb.get("max_hp", 1)
                bar_w = w
                bar_x = tb["x"]
                bar_y = tb["y"] - 8
                pygame.draw.rect(surface, (100, 0, 0), (bar_x, bar_y, bar_w, 6))
                if max_hp > 0:
                    pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, int(bar_w * (hp / max_hp)), 6))
            # Draw sword swing when active (angle-based arc)
            if tb.get("swinging") and tb.get("sword_rect"):
                try:
                    sx, sy, sw, sh = tb.get("sword_rect")
                    sword_img = load_image("objects/sword.png", sw, sh)
                    angle = tb.get("swing_angle", 0.0)
                    rotated = pygame.transform.rotate(sword_img, -angle)
                    if tb.get("swing_dir") == "left":
                        rotated = pygame.transform.flip(rotated, True, False)
                    surface.blit(rotated, (sx, sy))
                except Exception:
                    sx, sy, sw, sh = tb.get("sword_rect")
                    pygame.draw.rect(surface, (200, 200, 200), (sx, sy, sw, sh))
        except Exception:
            # fallback: draw rectangle
            pygame.draw.rect(surface, (200, 50, 200) if tb.get("boss") else (180, 60, 180), (int(tb["x"]), int(tb["y"]), w, h))

def draw_item(surface, x, y, item_type, item_id):
    """Draw items using images or procedural graphics."""
    
    level, row, col = current_room
    collected_set = get_collected_set(item_type)
    if (level, row, col, x, y) in collected_set:
        return None
    
    # Credits are drawn as coins (like bullet coins) instead of using image file
    if item_type == "credit":
        # Draw yellow/gold coin (matches bullet appearance)
        color_main = (255, 215, 0)
        color_inner = (255, 255, 100)
        pygame.draw.circle(surface, color_main, (int(x) + 10, int(y) + 10), 10)
        pygame.draw.circle(surface, color_inner, (int(x) + 10, int(y) + 10), 8)
        pygame.draw.circle(surface, (200, 180, 0), (int(x) + 10, int(y) + 10), 6)
        rect = pygame.Rect(x, y, 20, 20)
    else:
        img = load_item_image(item_type)
        surface.blit(img, (x, y))
        
        if item_type in ["key", "gold", "herb"]:
            rect = pygame.Rect(x, y, 45, 45)  
        elif item_type == "timeshard":
            rect = pygame.Rect(x, y, 50, 50)  
        else:
            rect = pygame.Rect(x, y, 25, 25)

    if item_type == "gold":
        gold_items.append((rect, x, y))
    elif item_type == "herb":
        herbs.append((rect, x, y))
    elif item_type == "potion":
        potions.append((rect, x, y))
    elif item_type == "timeshard":

        pass
    elif item_type == "key":

        pass
    
    return rect

def get_collected_set(item_type):
    if item_type == "gold":
        return collected_gold
    elif item_type == "herb":
        return collected_herbs
    elif item_type == "potion":
        return collected_potions
    elif item_type == "key":
        return collected_keys
    elif item_type == "timeshard":
        return collected_timeshards
    elif item_type == "credit":
        return collected_credits
    return set()

def draw_room(surface, level, row, col):
    """Draw the current room using images only."""
    global colliders, gold_items, herbs, potions, npcs, interactive_objects, damage_zones

    # clearing dynamic lists each frame keeps objects synced to the current room state
    colliders = []
    gold_items = []
    herbs = []
    potions = []
    npcs = []
    interactive_objects = []
    damage_zones = []

    room_key = (level, row, col)
    room_info = room_data.get(room_key, {})

    # draw background first so everything else sits on top
    bg_img = load_smart_bg(level, row, col)
    if bg_img:
        surface.blit(bg_img, (0, 0))
    else:
        # simple fallback background if an image is missing
        surface.fill((80, 120, 80))

    # place static objects like rocks and portal frame
    for obj in room_info.get("objects", []):
        draw_object(obj["x"], obj["y"], obj["type"], surface, level, obj["width"], obj["height"])

    # place interactive props such as levers and chests
    for inter in room_info.get("interactive", []):
        draw_object(inter["x"], inter["y"], inter["type"], surface, level, inter["width"], inter["height"])

    # draw friendly npcs while goblins and boss are handled elsewhere
    npcs_list = room_info.get("npcs", [])
    for i, npc in enumerate(npcs_list):
        if npc.get("id") in ["goblin", "boss1"]:
            continue

        # resolve dynamic state if present
        key = f"{level}_{row}_{col}_{npc.get('id')}_{i}"
        state = npc_states.get(key)

        # track if the knight has been rescued so we render the right state
        rescued = False
        if npc.get("id") == "knight":
            rescued = npc.get("rescued", False)

        if state:
            draw_npc(surface, int(state["x"]), int(state["y"]), npc["id"], rescued)
        else:
            draw_npc(surface, npc["x"], npc["y"], npc["id"], rescued)

    # Draw enemies
    draw_goblins(surface, room_key)
    draw_timebandits(surface, room_key)
    
    # Draw boss if in throne room
    if room_key == (0, 2, 0) and boss and boss["alive"]:
        draw_boss(surface)
    # Draw boss2 if in AI Control Room
    if room_key == (1, 2, 2) and boss2 and boss2.get("alive", False):
        draw_boss2(surface)
    
    # Draw boss drops if defeated
    if room_key == (0, 2, 0) and boss_defeated and not boss_drop_collected:
        draw_boss_drops(surface)

    # Draw items
    for item in room_info.get("items", []):
        draw_item(surface, item["x"], item["y"], item["type"], item.get("id", ""))

def draw_health_bar(surface):
    # always show the health bar near the bottom so the player knows their status
    """Draw permanent health bar at bottom middle of screen."""
    health_width = 400
    health_x = ROOM_WIDTH // 2 - health_width // 2
    health_y = ROOM_HEIGHT - 50
    

    pygame.draw.rect(surface, (100, 0, 0), (health_x, health_y, health_width, 30))

    pygame.draw.rect(surface, (0, 255, 0), (health_x, health_y, health_width * (health / max_health), 30))

    pygame.draw.rect(surface, (255, 255, 255), (health_x, health_y, health_width, 30), 2)
    

    health_text = font.render(f"Health: {int(health)}/{max_health}", True, (255, 255, 255))
    surface.blit(health_text, (health_x + 10, health_y + 5))
    

    armor_text = small_font.render(f"Armor Level: {armor_level}", True, (200, 255, 200))
    surface.blit(armor_text, (health_x + health_width - 150, health_y + 5))

def draw_hud(surface):
    # overlay that lets the player inspect inventory without pausing the world
    """Draw HUD with inventory (health bar is now drawn separately)."""
    if not hud_visible:
        return
    
    overlay = pygame.Surface((ROOM_WIDTH, ROOM_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    # Inventory
    y = 100
    for item, count in inventory.items():
        if count > 0:
            text = font.render(f"{item}: {count}", True, (255, 255, 255))
            surface.blit(text, (50, y))
            y += 30

def draw_minimap(surface, level, row, col):
    # small map to keep the player oriented inside the three by three grid
    """Draw minimap showing current room."""
    if not map_visible:
        return
    
    map_size = 150
    cell_size = map_size // 3
    map_x = ROOM_WIDTH - map_size - 20
    map_y = 20
    
    pygame.draw.rect(surface, (0, 0, 0, 180), (map_x - 5, map_y - 5, map_size + 10, map_size + 10))
    
    for r in range(3):
        for c in range(3):
            x = map_x + c * cell_size
            y = map_y + (2 - r) * cell_size  
            rect = pygame.Rect(x, y, cell_size - 2, cell_size - 2)
            
            # Check if this is the current room (note: r and row use same coordinate system)
            if r == row and c == col:
                pygame.draw.rect(surface, (255, 255, 0), rect)
            else:
                pygame.draw.rect(surface, (100, 100, 100), rect)
    
    room_name = room_data.get((level, row, col), {}).get("name", f"Room ({row},{col})")
    name_text = small_font.render(room_name, True, (255, 255, 255))
    surface.blit(name_text, (map_x, map_y + map_size + 10))

def draw_quest_log(surface):
    """Draw quest log."""
    if not quest_log_visible:
        return
    
    overlay = pygame.Surface((ROOM_WIDTH, ROOM_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    box = pygame.Rect(100, 100, 600, 500)
    pygame.draw.rect(surface, (20, 20, 40), box)
    pygame.draw.rect(surface, (255, 215, 0), box, 3)
    
    title = title_font.render("QUEST LOG", True, (255, 215, 0))
    surface.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, 120))
    
    y = 180
    for quest_id, quest_data in quests.items():
        if quest_data["active"]:
            color = (150, 255, 150) if quest_data["complete"] else (255, 255, 255)
            text = font.render(f"• {quest_data['description']}", True, color)
            surface.blit(text, (150, y))
            y += 40

def draw_message(surface):
    """Display temporary messages."""
    if message_timer > 0 and message:
        msg = font.render(message, True, message_color)
        rect = msg.get_rect(center=(ROOM_WIDTH // 2, 50))
        pygame.draw.rect(surface, (0, 0, 0), rect.inflate(20, 10))
        pygame.draw.rect(surface, message_color, rect.inflate(20, 10), 2)
        surface.blit(msg, rect)

def draw_dialogue(surface):
    """Display NPC dialogue."""
    if not dialogue_active or not current_dialogue:
        return
    
    box = pygame.Rect(50, ROOM_HEIGHT - 200, ROOM_WIDTH - 100, 150)
    pygame.draw.rect(surface, (20, 20, 40), box)
    pygame.draw.rect(surface, (255, 215, 0), box, 3)
    
    text = current_dialogue[dialogue_index]
    lines = []
    words = text.split(" ")
    line = ""
    
    for word in words:
        test = line + word + " "
        if font.size(test)[0] < ROOM_WIDTH - 150:
            line = test
        else:
            lines.append(line)
            line = word + " "
    lines.append(line)
    
    y = box.y + 20
    for line in lines:
        rendered = font.render(line, True, (255, 255, 255))
        surface.blit(rendered, (box.x + 20, y))
        y += 30
    
    hint = small_font.render("Press SPACE to continue...", True, (200, 200, 200))
    surface.blit(hint, (box.right - 180, box.bottom - 30))

def draw_blacksmith_shop(surface):
    """Draw the improved blacksmith shop interface."""
    if not upgrade_shop_visible:
        return
    
    overlay = pygame.Surface((ROOM_WIDTH, ROOM_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    surface.blit(overlay, (0, 0))
    

    shop_rect = pygame.Rect(50, 50, ROOM_WIDTH - 100, ROOM_HEIGHT - 100)
    pygame.draw.rect(surface, (40, 30, 20), shop_rect)
    pygame.draw.rect(surface, (180, 120, 50), shop_rect, 4)
    

    title_bg = pygame.Rect(shop_rect.x, shop_rect.y - 10, shop_rect.width, 70)
    pygame.draw.rect(surface, (60, 40, 20), title_bg)
    pygame.draw.rect(surface, (220, 180, 80), title_bg, 3)
    
    title = title_font.render("BLACKSMITH'S FORGE", True, (255, 200, 100))
    surface.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, shop_rect.y + 10))
    

    gold_rect = pygame.Rect(shop_rect.x + 20, shop_rect.y + 80, shop_rect.width - 40, 40)
    pygame.draw.rect(surface, (30, 30, 40), gold_rect)
    pygame.draw.rect(surface, (255, 215, 0), gold_rect, 2)
    
    gold_text = font.render(f"Your Gold: {inventory['Gold']}", True, (255, 215, 0))
    surface.blit(gold_text, (gold_rect.centerx - gold_text.get_width()//2, gold_rect.centery - gold_text.get_height()//2))
    

    stats_rect = pygame.Rect(shop_rect.x + 20, shop_rect.y + 130, shop_rect.width - 40, 60)
    pygame.draw.rect(surface, (30, 30, 40), stats_rect)
    pygame.draw.rect(surface, (100, 150, 200), stats_rect, 2)
    
    stats_lines = [
        f"Weapon: {'Equipped' if has_weapon else 'None'} (Lvl {weapon_level}) | Damage: {20 + (weapon_level * 5)}",
        f"Armor: Lvl {armor_level} | Health: {max_health} | Ammo: {ammo}/{max_ammo}",
        f"Ammo Packs bought (this level): {ammo_packs_bought.get(current_room[0],0)}/{MAX_AMMO_PACKS}"
    ]
    
    for i, line in enumerate(stats_lines):
        stat_text = small_font.render(line, True, (200, 220, 255))
        surface.blit(stat_text, (stats_rect.x + 10, stats_rect.y + 10 + i * 20))
    

    items_rect = pygame.Rect(shop_rect.x + 20, shop_rect.y + 210, shop_rect.width - 40, shop_rect.height - 280)
    pygame.draw.rect(surface, (50, 40, 30), items_rect)
    pygame.draw.rect(surface, (180, 150, 100), items_rect, 2)
    

    basic_header = font.render("BASIC ITEMS:", True, (255, 200, 100))
    upgrade_header = font.render("UPGRADES:", True, (255, 200, 100))
    surface.blit(basic_header, (items_rect.x + 10, items_rect.y + 10))
    surface.blit(upgrade_header, (items_rect.x + items_rect.width//2 + 10, items_rect.y + 10))
    
    # Draw shop items
    y_offset_basic = items_rect.y + 50
    y_offset_upgrade = items_rect.y + 50
    item_buttons = []
    
    for item_id, item_data in blacksmith_items.items():
        # Skip cyber-only items (laser/neon weapons) when in the medieval world (level 0)
        if item_data.get("cyber_only", False) and current_room[0] == 0:
            continue
        if item_data["type"] in ["weapon", "consumable"]:
            # Basic items column (left)
            item_bg = pygame.Rect(items_rect.x + 20, y_offset_basic, items_rect.width//2 - 60, 80)
            y_offset_basic += 100
        else:
            # Upgrades column (right) 
            item_bg = pygame.Rect(items_rect.x + items_rect.width//2 + 20, y_offset_upgrade, items_rect.width//2 - 60, 80)
            y_offset_upgrade += 100
        
        # Different background color based on purchase status and affordability
        if item_data.get("purchased", False):
            bg_color = (40, 60, 40)  # Greenish for purchased
            border_color = (100, 200, 100)
        elif inventory["Gold"] >= item_data["cost"] and _can_purchase_item(item_id):
            bg_color = (50, 50, 60)  # Normal for affordable
            border_color = (150, 150, 200)
        else:
            bg_color = (60, 40, 40)  # Reddish for unaffordable/can't purchase
            border_color = (200, 100, 100)
        
        pygame.draw.rect(surface, bg_color, item_bg)
        pygame.draw.rect(surface, border_color, item_bg, 3)
        
        # Item name and description
        name_text = font.render(item_data["name"], True, (255, 255, 255))
        desc_text = small_font.render(item_data["description"], True, (200, 200, 200))
        cost_text = font.render(f"{item_data['cost']} Gold", True, (255, 215, 0))
        
        surface.blit(name_text, (item_bg.x + 10, item_bg.y + 10))
        surface.blit(desc_text, (item_bg.x + 10, item_bg.y + 35))
        surface.blit(cost_text, (item_bg.right - 90, item_bg.y + 10))
        
        # Purchase status or button
        if item_data.get("purchased", False):
            status_text = font.render("PURCHASED", True, (100, 255, 100))
            surface.blit(status_text, (item_bg.right - 110, item_bg.y + 40))
        else:
            button_rect = pygame.Rect(item_bg.right - 100, item_bg.y + 40, 90, 30)
            can_purchase = inventory["Gold"] >= item_data["cost"] and _can_purchase_item(item_id)
            
            if can_purchase:
                pygame.draw.rect(surface, (80, 120, 80), button_rect)
                pygame.draw.rect(surface, (120, 200, 120), button_rect, 2)
                button_text = small_font.render("BUY", True, (200, 255, 200))
            else:
                pygame.draw.rect(surface, (120, 80, 80), button_rect)
                pygame.draw.rect(surface, (200, 120, 120), button_rect, 2)
                button_text = small_font.render("BUY", True, (255, 200, 200))
            
            surface.blit(button_text, (button_rect.centerx - button_text.get_width()//2, 
                                     button_rect.centery - button_text.get_height()//2))
            item_buttons.append((button_rect, item_id))
    

    close_rect = pygame.Rect(shop_rect.centerx - 50, shop_rect.bottom - 50, 100, 40)
    pygame.draw.rect(surface, (120, 80, 80), close_rect)
    pygame.draw.rect(surface, (200, 120, 120), close_rect, 2)
    close_text = font.render("CLOSE", True, (255, 255, 255))
    surface.blit(close_text, (close_rect.centerx - close_text.get_width()//2, 
                            close_rect.centery - close_text.get_height()//2))
    
    return item_buttons, close_rect


def _can_purchase_item(item_id):
    """Check if an item can be purchased based on game state."""
    item = blacksmith_items[item_id]
    
    if item_id == "weapon":
        return not item["purchased"] 
    
    elif item_id == "armor_upgrade":
        # Allow armor purchase only until the cap
        return armor_level < ARMOR_MAX_LEVEL
    
    elif item_id == "weapon_upgrade":
        return has_weapon and weapon_level < 5  
    
    elif item_id in ["ammo_pack", "health_potion"]:
        # Ammo packs limited per level, health potions unlimited
        if item_id == "ammo_pack":
            level = current_room[0]
            return ammo_packs_bought.get(level, 0) < MAX_AMMO_PACKS
        return True 
    
    return False

def handle_blacksmith_purchase(item_id):
    """Handle purchasing items from the blacksmith."""
    global has_weapon, ammo, max_ammo, health, max_health, inventory, weapon_level, armor_level
    
    item = blacksmith_items[item_id]
    
    if item.get("purchased", False):
        set_message(f"You already purchased the {item['name']}!", (255, 200, 0), 2.0)
        return False
    
    if inventory["Gold"] < item["cost"]:
        set_message(f"Not enough gold for {item['name']}!", (255, 0, 0), 2.0)
        return False
    
    if not _can_purchase_item(item_id):
        if item_id == "weapon_upgrade" and not has_weapon:
            set_message("You need to buy a weapon first!", (255, 200, 0), 2.0)
        elif item_id == "weapon_upgrade" and weapon_level >= 5:
            set_message("Weapon is already at maximum level!", (255, 200, 0), 2.0)
        elif item_id == "armor_upgrade" and armor_level >= ARMOR_MAX_LEVEL:
            set_message("Armor is already at maximum level!", (255, 200, 0), 2.0)
        else:
            set_message(f"Cannot purchase {item['name']} right now!", (255, 200, 0), 2.0)
        return False
    

    inventory["Gold"] -= item["cost"]
    

    if item_id == "weapon":
        item["purchased"] = True
        has_weapon = True
        ammo = max_ammo 
        set_message(f"Purchased {item['name']}! You can now shoot with SPACE.", (0, 255, 0), 3.0)
        quests["buy_weapon"]["complete"] = True
        quests["upgrade_sword"]["active"] = True
    
    elif item_id == "ammo_pack":
        # Increment per-level ammo pack counter and add one pack to inventory
        level = current_room[0]
        ammo_packs_bought[level] = ammo_packs_bought.get(level, 0) + 1
        inventory["Ammo Packs"] = inventory.get("Ammo Packs", 0) + 1
        set_message(f"Purchased {item['name']} ({ammo_packs_bought[level]}/{MAX_AMMO_PACKS})! Ammo Packs: {inventory['Ammo Packs']}", (0, 255, 0), 2.0)
    
    elif item_id == "health_potion":
        health = min(max_health, health + 30)
        set_message(f"Used {item['name']}! +30 Health", (0, 255, 0), 2.0)
    
    elif item_id == "armor_upgrade":
        # Increase armor level, scale max health, and preserve current health percentage
        prev_max = max_health
        armor_level += 1
        max_health = 100 + (armor_level * 20)
        if prev_max > 0:
            health = min(max_health, int((health / prev_max) * max_health))
        else:
            health = max_health
        set_message(f"Armor upgraded to level {armor_level}! Max health: {max_health}", (0, 255, 0), 2.0)
        # Double the cost for the next armor upgrade
        try:
            item["cost"] = int(item.get("cost", 0) * 2)
        except Exception:
            pass
    
    elif item_id == "weapon_upgrade":
        weapon_level += 1
        set_message(f"Weapon upgraded to level {weapon_level}! Damage: {20 + (weapon_level * 5)}", (0, 255, 0), 2.0)
        

        if weapon_level >= 5:
            item["purchased"] = True
    
    return True


def draw_safe_puzzle(surface):
    """Draw the safe puzzle interface."""
    if not safe_visible:
        return
    
    overlay = pygame.Surface((ROOM_WIDTH, ROOM_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    box = pygame.Rect(200, 200, 400, 300)
    pygame.draw.rect(surface, (50, 50, 70), box)
    pygame.draw.rect(surface, (200, 180, 50), box, 4)
    
    title = font.render("SAFE LOCK", True, (255, 215, 0))
    surface.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, 220))
    
    # Display current input
    input_text = font.render(f"Code: {safe_input}", True, (255, 255, 255))
    surface.blit(input_text, (ROOM_WIDTH//2 - input_text.get_width()//2, 280))
    
    if safe_unlocked:
        success_text = font.render("SAFE UNLOCKED! Key found!", True, (0, 255, 0))
        surface.blit(success_text, (ROOM_WIDTH//2 - success_text.get_width()//2, 320))
    else:
        hint_text = small_font.render("Enter the 4-digit code", True, (200, 200, 200))
        surface.blit(hint_text, (ROOM_WIDTH//2 - hint_text.get_width()//2, 320))
    
    # Number buttons - repositioned to avoid overlap
    button_size = 50
    buttons = []
    for i in range(3):
        for j in range(3):
            num = i * 3 + j + 1
            x = box.x + 100 + j * 60
            y = box.y + 150 + i * 60
            button_rect = pygame.Rect(x, y, button_size, button_size)
            pygame.draw.rect(surface, (80, 80, 100), button_rect)
            pygame.draw.rect(surface, (200, 200, 220), button_rect, 2)
            
            num_text = font.render(str(num), True, (255, 255, 255))
            surface.blit(num_text, (x + button_size//2 - num_text.get_width()//2, 
                                  y + button_size//2 - num_text.get_height()//2))
            buttons.append((button_rect, str(num)))
    
    # Clear button - moved to avoid overlapping with number 1
    clear_rect = pygame.Rect(box.x + 50, box.y + 270, 80, 40)  
    pygame.draw.rect(surface, (180, 80, 80), clear_rect)
    pygame.draw.rect(surface, (220, 150, 150), clear_rect, 2)
    clear_text = small_font.render("CLEAR", True, (255, 255, 255))
    surface.blit(clear_text, (clear_rect.centerx - clear_text.get_width()//2, 
                            clear_rect.centery - clear_text.get_height()//2))
    
    # Close button - moved to avoid overlapping
    close_rect = pygame.Rect(box.x + 270, box.y + 270, 80, 40)  
    pygame.draw.rect(surface, (80, 80, 180), close_rect)
    pygame.draw.rect(surface, (150, 150, 220), close_rect, 2)
    close_text = small_font.render("CLOSE", True, (255, 255, 255))
    surface.blit(close_text, (close_rect.centerx - close_text.get_width()//2, 
                            close_rect.centery - close_text.get_height()//2))
    
    return buttons, clear_rect, close_rect

def draw_maze_puzzle(surface):
    """Draw the maze puzzle interface."""
    if not maze_visible:
        return
    
    overlay = pygame.Surface((ROOM_WIDTH, ROOM_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    # Calculate maze position to center it
    maze_total_width = maze_width * maze_cell_size
    maze_total_height = maze_height * maze_cell_size
    maze_x = (ROOM_WIDTH - maze_total_width) // 2
    maze_y = (ROOM_HEIGHT - maze_total_height) // 2
    
    # Draw maze background
    maze_bg = pygame.Rect(maze_x - 10, maze_y - 40, maze_total_width + 20, maze_total_height + 80)
    pygame.draw.rect(surface, (40, 40, 60), maze_bg)
    pygame.draw.rect(surface, (255, 215, 0), maze_bg, 3)
    
    # Draw title
    title = font.render("MAZE PUZZLE - Free the Knight!", True, (255, 215, 0))
    surface.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, maze_y - 30))
    
    # Draw instructions
    instructions = small_font.render("Use arrow keys to navigate to the exit (green square)", True, (200, 200, 200))
    surface.blit(instructions, (ROOM_WIDTH//2 - instructions.get_width()//2, maze_y + maze_total_height + 10))
    
    # Draw maze
    for y in range(maze_height):
        for x in range(maze_width):
            cell_x = maze_x + x * maze_cell_size
            cell_y = maze_y + y * maze_cell_size
            cell_rect = pygame.Rect(cell_x, cell_y, maze_cell_size, maze_cell_size)
            
            if maze_layout[y][x] == 1:  # Wall
                pygame.draw.rect(surface, (80, 80, 120), cell_rect)
                pygame.draw.rect(surface, (100, 100, 150), cell_rect, 1)
            else:  # Path
                pygame.draw.rect(surface, (30, 30, 50), cell_rect)
                pygame.draw.rect(surface, (60, 60, 90), cell_rect, 1)
    
    # Draw exit
    exit_x = maze_x + maze_exit_pos[0] * maze_cell_size
    exit_y = maze_y + maze_exit_pos[1] * maze_cell_size
    exit_rect = pygame.Rect(exit_x, exit_y, maze_cell_size, maze_cell_size)
    pygame.draw.rect(surface, (0, 200, 0), exit_rect)
    pygame.draw.rect(surface, (0, 255, 0), exit_rect, 2)
    
    # Draw player
    player_x = maze_x + maze_player_pos[0] * maze_cell_size
    player_y = maze_y + maze_player_pos[1] * maze_cell_size
    player_rect = pygame.Rect(player_x + 5, player_y + 5, maze_cell_size - 10, maze_cell_size - 10)
    pygame.draw.rect(surface, (255, 100, 100), player_rect)
    
    # Draw close button
    close_rect = pygame.Rect(maze_x + maze_total_width - 90, maze_y + maze_total_height + 10, 80, 25)
    pygame.draw.rect(surface, (180, 80, 80), close_rect)
    pygame.draw.rect(surface, (220, 150, 150), close_rect, 2)
    close_text = small_font.render("CLOSE", True, (255, 255, 255))
    surface.blit(close_text, (close_rect.centerx - close_text.get_width()//2, 
                            close_rect.centery - close_text.get_height()//2))
    
    return close_rect

def handle_maze_input():
    """Handle arrow key input for maze navigation."""
    global maze_player_pos, maze_completed
    
    keys = pygame.key.get_pressed()
    new_pos = maze_player_pos.copy()
    
    if keys[pygame.K_UP]:
        new_pos[1] -= 1
    elif keys[pygame.K_DOWN]:
        new_pos[1] += 1
    elif keys[pygame.K_LEFT]:
        new_pos[0] -= 1
    elif keys[pygame.K_RIGHT]:
        new_pos[0] += 1
    else:
        return False
    
    # Check if move is valid (within bounds and not a wall)
    if (0 <= new_pos[0] < maze_width and 0 <= new_pos[1] < maze_height and 
        maze_layout[new_pos[1]][new_pos[0]] == 0):
        maze_player_pos = new_pos
        
        # Check if reached exit
        if maze_player_pos == maze_exit_pos:
            maze_completed = True
            maze_visible = False
           
            room_key = tuple(current_room)
            room_info = room_data.get(room_key, {})
            for npc in room_info.get("npcs", []):
                if npc.get("id") == "knight":
                    npc["rescued"] = True
                    npc["x"] = 500  
                    npc["y"] = 450
                    quests["rescue_knight"]["complete"] = True
                    quests["defeat_goblin_king"]["active"] = True
                    # Drop a key near the cage
                    room_info["items"].append({"type": "key", "x": 450, "y": 500, "id": "key_0_1_0_2"})
                    set_message("Knight rescued! He dropped a key!", (0, 255, 0), 3.0)
                    break
        return True
    return False

def draw_cipher_overlay(surface):
    """Draw the Data Hub cipher overlay when active."""
    if not cipher_visible:
        return
    
    # Ensure cipher_text_shifted is defined
    if not cipher_text_shifted:
        return

    overlay = pygame.Surface((ROOM_WIDTH, ROOM_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    surface.blit(overlay, (0, 0))

    box = pygame.Rect(150, 180, 500, 300)
    pygame.draw.rect(surface, (10, 20, 30), box)
    pygame.draw.rect(surface, (0, 200, 255), box, 3)

    title = title_font.render("DATA HUB", True, (0, 255, 255))
    surface.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, box.y + 10))

    shifted_text = small_font.render(f"Cipher: {cipher_text_shifted}", True, (200, 200, 255))
    surface.blit(shifted_text, (box.x + 20, box.y + 80))

    prompt = small_font.render("Enter decoded phrase and press ENTER:", True, (200, 200, 200))
    surface.blit(prompt, (box.x + 20, box.y + 120))

    input_box = pygame.Rect(box.x + 20, box.y + 150, box.width - 40, 40)
    pygame.draw.rect(surface, (30, 30, 50), input_box)
    pygame.draw.rect(surface, (100, 100, 150), input_box, 2)

    input_text_surf = font.render(cipher_input, True, (255, 255, 255))
    surface.blit(input_text_surf, (input_box.x + 10, input_box.y + 6))

    hint = small_font.render("Hint: It's a simple Caesar shift", True, (150, 150, 200))
    surface.blit(hint, (box.x + 20, box.y + 210))

    close_rect = pygame.Rect(box.centerx - 50, box.bottom - 50, 100, 36)
    pygame.draw.rect(surface, (100, 0, 100), close_rect)
    pygame.draw.rect(surface, (255, 0, 255), close_rect, 2)
    close_text = small_font.render("CLOSE", True, (255, 255, 255))
    surface.blit(close_text, (close_rect.centerx - close_text.get_width()//2, close_rect.centery - close_text.get_height()//2))

    return close_rect

# ===== NEW UI FUNCTIONS =====
def create_button(text, x, y, width, height, hover=False):
    """Create a button with hover effect."""
    button_color = (80, 80, 120) if not hover else (100, 100, 150)
    border_color = (150, 150, 200) if not hover else (180, 180, 220)
    
    button_rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(screen, button_color, button_rect)
    pygame.draw.rect(screen, border_color, button_rect, 3)
    
    text_surf = button_font.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=button_rect.center)
    screen.blit(text_surf, text_rect)
    
    return button_rect

def draw_main_menu():
    """Draw the main menu with options."""
    screen.fill((20, 20, 40))
    
    # Title
    title = title_font.render("CHRONICLES OF TIME", True, (255, 215, 0))
    subtitle = font.render("An Epic Time-Travel Adventure", True, (200, 200, 255))
    screen.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, 150))
    screen.blit(subtitle, (ROOM_WIDTH//2 - subtitle.get_width()//2, 220))
    
    # Buttons
    button_width, button_height = 300, 60
    button_x = ROOM_WIDTH//2 - button_width//2
    
    play_button = create_button("PLAY", button_x, 300, button_width, button_height, play_button_hover)
    how_to_button = create_button("HOW TO PLAY", button_x, 380, button_width, button_height, how_to_button_hover)
    about_button = create_button("ABOUT", button_x, 460, button_width, button_height, about_button_hover)
    
    # Footer
    footer = small_font.render("Made by Arjun Tambe, Shuban Nannisetty and Charanjit Kukkadapu.", True, (150, 150, 150))
    screen.blit(footer, (ROOM_WIDTH//2 - footer.get_width()//2, ROOM_HEIGHT - 40))
    
    return play_button, how_to_button, about_button

def draw_how_to_play():
    """Draw the how to play screen."""
    screen.fill((20, 20, 40))
    
    # Title
    title = title_font.render("HOW TO PLAY", True, (255, 215, 0))
    screen.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, 80))
    
    # Content box
    content_box = pygame.Rect(50, 150, ROOM_WIDTH - 100, ROOM_HEIGHT - 250)
    pygame.draw.rect(screen, (30, 30, 50), content_box)
    pygame.draw.rect(screen, (255, 215, 0), content_box, 3)
    
    # Instructions
    instructions = [
        "CONTROLS:",
        "• WASD or Arrow Keys - Move character",
        "• SPACE - Shoot weapon",
        "• R - Reload weapon", 
        "• F - Interact with objects/NPCs",
        "• G - Give herbs to Herb Collector",
        "• E - Toggle Inventory",
        "• M - Toggle Minimap",
        "• Q - Toggle Quest Log",
        "• H - Use Health Potion",
        "",
        "GAMEPLAY:",
        "• Explore different rooms and eras",
        "• Collect gold, herbs, and potions",
        "• Complete quests from NPCs",
        "• Upgrade your weapon and armor",
        "• Solve challenging puzzles and riddles",
        "• Find Time Shards to travel through time",
        "• Defeat the Goblin King boss in the Throne Room"
    ]
    
    y = content_box.y + 20
    for line in instructions:
        if "CONTROLS:" in line or "GAMEPLAY:" in line:
            text = font.render(line, True, (255, 180, 0))
        else:
            text = small_font.render(line, True, (220, 220, 220))
        screen.blit(text, (content_box.x + 20, y))
        y += 30
    
    # Back button
    back_button = create_button("BACK", ROOM_WIDTH//2 - 100, ROOM_HEIGHT - 80, 200, 50, back_button_hover)
    return back_button

def draw_about():
    """Draw the about screen."""
    screen.fill((20, 20, 40))
    
    # Title
    title = title_font.render("ABOUT", True, (255, 215, 0))
    screen.blit(title, (ROOM_WIDTH//2 - title.get_width()//2, 80))
    
    # Content box
    content_box = pygame.Rect(50, 150, ROOM_WIDTH - 100, ROOM_HEIGHT - 250)
    pygame.draw.rect(screen, (30, 30, 50), content_box)
    pygame.draw.rect(screen, (255, 215, 0), content_box, 3)
    
    # About text
    about_text = [
        "CHRONICLES OF TIME",
        "",
        "Embark on an epic time-travel adventure across different eras!",
        "",
        "STORY:",
        "You are Arin, a brave adventurer tasked with recovering the",
        "lost Time Shards that have been scattered throughout history.",
        "Your journey will take you from peaceful villages to ancient",
        "castles and mysterious libraries.",
        "",
        "FEATURES:",
        "• Explore 9 unique rooms across different time periods",
        "• Engage in combat with various enemies",
        "• Solve challenging puzzles and riddles",
        "• Upgrade your equipment and abilities",
        "• Complete quests and uncover the story",
        "• Collect valuable items and resources",
        "• Defeat the mighty Goblin King boss",
        "",
        "Can you restore the timeline and save the world?"
    ]
    
    y = content_box.y + 20
    for line in about_text:
        if "CHRONICLES OF TIME" in line:
            text = font.render(line, True, (255, 180, 0))
        elif "STORY:" in line or "FEATURES:" in line:
            text = small_font.render(line, True, (200, 200, 255))
        else:
            text = small_font.render(line, True, (220, 220, 220))
        screen.blit(text, (content_box.x + 20, y))
        y += 25
    
    # Back button
    back_button = create_button("BACK", ROOM_WIDTH//2 - 100, ROOM_HEIGHT - 80, 200, 50, back_button_hover)
    return back_button

#  GAME LOGIC FUNCTIONS 
def collision_check(dx, dy):
    """Handle collision with objects."""
    player.x += dx
    for collider in colliders:
        if player.colliderect(collider):
            if dx > 0:
                player.right = collider.left
            elif dx < 0:
                player.left = collider.right
    
    player.y += dy
    for collider in colliders:
        if player.colliderect(collider):
            if dy > 0:
                player.bottom = collider.top
            elif dy < 0:
                player.top = collider.bottom

def room_transition():
    """Handle moving between rooms."""
    level, row, col = current_room
    
    if player.right > ROOM_WIDTH:
        if col < GRID_WIDTH - 1:
            current_room[2] += 1
            player.left = 0
        else:
            player.right = ROOM_WIDTH
    
    elif player.top < 0:
        if row < GRID_HEIGHT - 1:
            current_room[1] += 1
            player.bottom = ROOM_HEIGHT
        else:
            player.top = 0
    
    elif player.bottom > ROOM_HEIGHT:
        if row > 0:
            current_room[1] -= 1
            player.top = 0
        else:
            player.bottom = ROOM_HEIGHT
    elif player.left < 0:
        if col > 0:
            # ------ Market → Rooftop  ONLY ------
            if current_room[0] == 1 and current_room[1] == 0 and current_room[2] == 1:  # still IN market
                current_room[2] = 0          
                player.center = (625, 450)  # spawn point when entering Rooftop from Market
                return                      
            current_room[2] -= 1
            player.right = ROOM_WIDTH
        else:
            player.left = 0

def update_goblins(dt):
    """Move goblins toward the player in the Forest Path."""
    room_key = tuple(current_room)
    state = goblin_rooms.get(room_key)
    if not state:
        return
    if dialogue_active or hud_visible or quest_log_visible or upgrade_shop_visible or maze_visible:
        return
    global goblin_contact_cooldown, health

    dt_sec = dt / 1000.0
    goblin_contact_cooldown = max(0.0, goblin_contact_cooldown - dt_sec)

    # Spawn next wave when current is cleared
    if not any(g.get("alive", True) for g in state["active"]):
        if state["wave_index"] < len(state["waves"]):
            state["respawn"] -= dt_sec
            if state["respawn"] <= 0:
                spawn = state["waves"][state["wave_index"]]
                state["active"] = [{"x": float(x), "y": float(y), "alive": True, "loot_given": False} for x, y in spawn]
                state["wave_index"] += 1
                state["respawn"] = 1.0  # prepare next delay
                set_message("Goblins incoming!", (255, 180, 50), 1.0)
        return

    # Chase the player
    w, h = get_npc_size("goblin")
    speed = 140  
    for goblin in state["active"]:
        if not goblin.get("alive", True):
            continue
        gx = goblin["x"] + w / 2
        gy = goblin["y"] + h / 2
        dx = player.centerx - gx
        dy = player.centery - gy
        dist = math.hypot(dx, dy)
        if dist <= 1:
            continue
        step = speed * dt_sec
        goblin["x"] += (dx / dist) * step
        goblin["y"] += (dy / dist) * step
        goblin["x"] = max(0, min(ROOM_WIDTH - w, goblin["x"]))
        goblin["y"] = max(0, min(ROOM_HEIGHT - h, goblin["y"]))

        # Contact damage
        goblin_rect = pygame.Rect(goblin["x"], goblin["y"], w, h)
        if goblin_rect.colliderect(player) and goblin_contact_cooldown <= 0:
            health = max(0, health - GOBLIN_CONTACT_DAMAGE)
            goblin_contact_cooldown = 0.75
            set_message(f"-{GOBLIN_CONTACT_DAMAGE} HP (Goblin)", (255, 80, 80), 1.0)


def update_npcs(dt):
    """Update roaming for friendly NPCs in the current room.
    NPCs continuously move around within their roam_radius at a slow speed.
    They stop moving when the player is within `stop_distance` or when flagged as talking.
    NPCs also avoid colliding with invisible barriers.
    """
    dt_sec = dt / 1000.0
    room_key = tuple(current_room)
    
    # Get barriers from current room (invisible colliders)
    room_info = room_data.get(room_key, {})
    barriers = []
    for obj in room_info.get("objects", []):
        if obj.get("type") == "invisible":
            barriers.append(pygame.Rect(obj["x"], obj["y"], obj["width"], obj["height"]))
    
    # iterate states for NPCs in this room
    for key, state in npc_states.items():
        if tuple(state.get("room_key")) != room_key:
            continue

        # if NPC is talking or player is near, halt movement
        px, py = player.centerx, player.centery
        dist_to_player = math.hypot(px - (state["x"] + 0), py - (state["y"] + 0))
        if state.get("talking") or dist_to_player <= state.get("stop_distance", 120):
            state["target"] = None
            continue

        # pick a new target when none present (continuously move)
        if not state.get("target"):
            angle = random.random() * math.pi * 2
            r = random.uniform(0, state.get("roam_radius", 80))
            tx = state["home_x"] + math.cos(angle) * r
            ty = state["home_y"] + math.sin(angle) * r
            # clamp to room bounds
            tx = max(0, min(ROOM_WIDTH - 32, tx))
            ty = max(0, min(ROOM_HEIGHT - 32, ty))
            state["target"] = (tx, ty)
        else:
            tx, ty = state["target"]
            dx = tx - state["x"]
            dy = ty - state["y"]
            d = math.hypot(dx, dy)
            if d <= 2:
                # reached target; pick a new one immediately
                state["target"] = None
            else:
                speed = state.get("speed", 30)
                step = speed * dt_sec
                new_x = state["x"] + (dx / d) * min(step, d)
                new_y = state["y"] + (dy / d) * min(step, d)
                
                # check collision with barriers
                npc_size = get_npc_size(state["id"])
                test_rect = pygame.Rect(int(new_x), int(new_y), npc_size[0], npc_size[1])
                
                # only move if no collision
                collision = False
                for barrier in barriers:
                    if test_rect.colliderect(barrier):
                        collision = True
                        break
                
                if not collision:
                    state["x"] = new_x
                    state["y"] = new_y
                else:
                    # pick a new target to avoid barrier
                    state["target"] = None


def update_timebandits(dt):
    """Move Time Bandits toward the player in configured cyber rooms."""
    room_key = tuple(current_room)
    state = timebandit_rooms.get(room_key)
    if not state:
        return
    if dialogue_active or hud_visible or quest_log_visible or upgrade_shop_visible or maze_visible:
        return
    global goblin_contact_cooldown, health, player_electrified_timer

    dt_sec = dt / 1000.0

    # Spawn next wave when current is cleared
    if not any(tb.get("alive", True) for tb in state["active"]):
        if state["wave_index"] < len(state["waves"]):
            state["respawn"] -= dt_sec
            if state["respawn"] <= 0:
                idx = state["wave_index"]
                spawn = state["waves"][idx]
                state["active"] = [{"x": float(x), "y": float(y), "alive": True, "loot_given": False} for x, y in spawn]
                # If this is the second wave (index 1), add a miniboss
                if idx == 1:
                    default_w, default_h = get_npc_size("timebandit")
                    # slightly smaller than before (3x instead of 4x)
                    miniboss_w = int(default_w * 3)
                    miniboss_h = int(default_h * 3)
                    miniboss_x = ROOM_WIDTH // 2 - miniboss_w // 2
                    miniboss_y = ROOM_HEIGHT // 2 - miniboss_h // 2
                    miniboss = {
                        "x": float(miniboss_x),
                        "y": float(miniboss_y),
                        "alive": True,
                        "loot_given": False,
                        "boss": True,
                        "is_miniboss": True,
                        "hp": TIMEBANDIT_BASE_HP * 5,
                        "max_hp": TIMEBANDIT_BASE_HP * 5,
                        # miniboss sword damage (hits from sword should do 5 HP)
                        "damage": 5,
                        "w": miniboss_w,
                        "h": miniboss_h,
                        # swing attack state
                        "swing_cooldown": random.uniform(2.0, 4.0),
                        "swing_timer": 0.0,
                        "swing_active": False,
                        "swing_hit": False,
                        "swing_rect": None,
                    }
                    state["active"].append(miniboss)
                    set_message("A MINIBOSS approaches!", (255, 120, 180), 2.5)
                state["wave_index"] += 1
                state["respawn"] = 1.0
                set_message("Time Bandits incoming!", (200, 80, 255), 1.5)
        return

    # Chase the player
    default_w, default_h = get_npc_size("timebandit")
    speed = 160
    for tb in state["active"]:
        if not tb.get("alive", True):
            continue
        w = tb.get("w", default_w)
        h = tb.get("h", default_h)
        gx = tb["x"] + w / 2
        gy = tb["y"] + h / 2
        dx = player.centerx - gx
        dy = player.centery - gy
        dist = math.hypot(dx, dy)
        if dist <= 1:
            continue
        step = speed * dt_sec
        tb["x"] += (dx / dist) * step
        tb["y"] += (dy / dist) * step
        tb["x"] = max(0, min(ROOM_WIDTH - w, tb["x"]))
        tb["y"] = max(0, min(ROOM_HEIGHT - h, tb["y"]))

        # Contact damage: miniboss does NOT deal contact damage (only sword swing does)
        tb_rect = pygame.Rect(tb["x"], tb["y"], int(w), int(h))
        if not tb.get("is_miniboss"):
            tb_damage = tb.get("damage", TIMEBANDIT_BASE_DAMAGE)
            if tb_rect.colliderect(player) and goblin_contact_cooldown <= 0:
                health = max(0, health - tb_damage)
                player_electrified_timer = 3.0  # Electrified for 3 seconds
                goblin_contact_cooldown = 0.75
                set_message("You are ELECTRIFIED!", (0, 200, 255), 2.0)

    # Simple separation to avoid stacking: push bandits apart
    min_sep = (default_w + default_h) / 4
    for i, a in enumerate(state["active"]):
        if not a.get("alive", True):
            continue
        aw = a.get("w", default_w)
        ah = a.get("h", default_h)
        ax = a["x"] + aw / 2
        ay = a["y"] + ah / 2
        for j, b in enumerate(state["active"]):
            if i == j or not b.get("alive", True):
                continue
            bw = b.get("w", default_w)
            bh = b.get("h", default_h)
            bx = b["x"] + bw / 2
            by = b["y"] + bh / 2
            ddx = ax - bx
            ddy = ay - by
            d = math.hypot(ddx, ddy)
            if d <= 0:
                continue
            overlap = (min_sep - d)
            if overlap > 0:
                push = overlap * 0.5
                nx = ddx / d
                ny = ddy / d
                a["x"] += nx * push
                a["y"] += ny * push
                b["x"] -= nx * push
                b["y"] -= ny * push
                # clamp
                a["x"] = max(0, min(ROOM_WIDTH - aw, a["x"]))
                a["y"] = max(0, min(ROOM_HEIGHT - ah, a["y"]))
                b["x"] = max(0, min(ROOM_WIDTH - bw, b["x"]))
                b["y"] = max(0, min(ROOM_HEIGHT - bh, b["y"]))

    # Handle miniboss swing attacks using an arc (angle) like the main boss
    for tb in state["active"]:
        if not tb.get("alive", True) or not tb.get("is_miniboss"):
            continue
        # initialize fields
        tb.setdefault("swing_cooldown", random.uniform(2.0, 4.0))
        tb.setdefault("swing_angle", 0.0)
        tb.setdefault("swinging", False)
        tb.setdefault("swing_duration", 0.45)
        tb.setdefault("swing_dir", "right")
        tb.setdefault("sword_rect", None)

        if not tb["swinging"]:
            tb["swing_cooldown"] -= dt_sec
            if tb["swing_cooldown"] <= 0:
                # start swing
                tb["swinging"] = True
                tb["swing_angle"] = 0.0
                tb["swing_dir"] = "left" if player.centerx < (tb["x"] + tb.get("w", default_w)/2) else "right"
                tb["swing_cooldown"] = random.uniform(2.0, 4.0)
        else:
            # progress swing angle to 180 over swing_duration
            swing_dur = max(0.05, tb.get("swing_duration", 0.45))
            angle_speed = 180.0 / swing_dur
            tb["swing_angle"] += angle_speed * dt_sec

            # compute sword position similar to calculate_axe_rect but scaled to miniboss
            w = tb.get("w", default_w)
            h = tb.get("h", default_h)
            center_x = tb["x"] + w/2
            center_y = tb["y"] + h/2
            radius = max(w, h) * 0.9
            angle_rad = math.radians(tb["swing_angle"]) if tb.get("swing_dir") == "right" else math.radians(tb["swing_angle"])

            if tb.get("swing_dir") == "right":
                sx = center_x + radius * math.cos(angle_rad)
                sy = center_y + radius * math.sin(angle_rad)
            else:
                sx = center_x - radius * math.cos(angle_rad)
                sy = center_y + radius * math.sin(angle_rad)

            # sword rect for collision/drawing
            sword_w = int(w * 0.6)
            sword_h = int(h * 0.4)
            tb["sword_rect"] = (int(sx - sword_w/2), int(sy - sword_h/2), sword_w, sword_h)

            # when swing finishes, check collision and apply damage once
            if tb["swing_angle"] >= 180.0:
                tb["swinging"] = False
                tb["swing_angle"] = 0.0
                sr = pygame.Rect(*tb["sword_rect"]) if tb.get("sword_rect") else None
                # ensure the sword hit registers even if the player is overlapping the miniboss body
                miniboss_rect = pygame.Rect(int(tb["x"]), int(tb["y"]), int(w), int(h))
                if (sr and player.colliderect(sr)) or player.colliderect(miniboss_rect):
                    dmg = tb.get("damage", 5)
                    health = max(0, health - dmg)
                    set_message(f"-{dmg} HP (Miniboss Sword)", (255, 80, 80), 1.5)
                tb["sword_rect"] = None

def pickup_items():
    """Handle item collection."""
    global message, message_timer, message_color, health, player_speed_boost_timer
    
    for rect, x, y in gold_items:
        if player.colliderect(rect):
            inventory["Gold"] += 10
            collected_gold.add((*current_room, x, y))
            set_message("+10 Gold", (255, 215, 0), 1.5)
    
    for rect, x, y in herbs:
        if player.colliderect(rect):
            inventory["Herbs"] += 1
            collected_herbs.add((*current_room, x, y))
            set_message("+1 Herb", (0, 255, 0), 1.5)
    
    for rect, x, y in potions:
        if player.colliderect(rect):
            inventory["Health Potions"] += 1
            collected_potions.add((*current_room, x, y))


            if tuple(current_room) == (0, 1, 2):
                global health, player_speed_boost_timer
                player_speed_boost_timer = 8.0
                health = min(max_health, health + 30)
                set_message("+1 Health Potion (Boost active!)", (0, 255, 0), 1.8)
            else:
                set_message("+1 Health Potion", (255, 0, 0), 1.5)
    
    # Handle key and time shard pickup
    room_key = tuple(current_room)
    room_info = room_data.get(room_key, {})
    for item in list(room_info.get("items", [])):
        itype = item.get("type")
        # create appropriate rect sizes
        if itype == "key":
            item_rect = pygame.Rect(item["x"], item["y"], 45, 45)
        elif itype == "timeshard":
            item_rect = pygame.Rect(item["x"], item["y"], 50, 50)
        elif itype == "keycard":
            item_rect = pygame.Rect(item["x"], item["y"], 45, 45)
        elif itype == "credit":
            item_rect = pygame.Rect(item["x"], item["y"], 20, 20)
        else:
            item_rect = pygame.Rect(item.get("x", 0), item.get("y", 0), 25, 25)

        if player.colliderect(item_rect.inflate(20, 20)):
            key_tuple = (room_key[0], room_key[1], room_key[2], item["x"], item["y"])
            # Key pickup behaves as before
            if itype == "key" and key_tuple not in collected_keys:
                inventory["Keys"] += 1
                collected_keys.add(key_tuple)
                set_message("+1 Key", (255, 215, 0), 1.5)
                break

            # Keycard pickup: remove keycard and reward player
            elif itype == "keycard" and key_tuple not in collected_keys:
                collected_keys.add(key_tuple)
                # Remove the keycard from the room so it disappears
                try:
                    room_info["items"].remove(item)
                except Exception:
                    pass
                # Reward the player for collecting the keycard
                inventory["Gold"] += 50
                set_message("+50 Gold (Keycard collected)", (255, 215, 0), 2.5)
                break

            # Credit pickup -> +25 credits (Gold)
            elif itype == "credit" and key_tuple not in collected_credits:
                inventory["Gold"] += 25
                collected_credits.add(key_tuple)
                set_message("+25 Credits", (255, 215, 0), 1.5)
                break

            elif itype == "timeshard" and key_tuple not in collected_timeshards:
                inventory["Time Shards"] += 1
                collected_timeshards.add(key_tuple)
                set_message("+1 Time Shard!", (150, 150, 255), 2.0)
                break

def set_message(text, color, duration):
    """Helper to queue on-screen messages safely."""
    global message, message_timer, message_color
    message, message_color, message_timer = text, color, duration

def handle_interaction():
    """Handle F key interactions."""
    global dialogue_active, current_dialogue, dialogue_index, upgrade_shop_visible
    global safe_visible, safe_input, safe_unlocked, maze_visible, cyber_shop_visible
    
    room_key = tuple(current_room)
    
    # Check for Blacksmith anvil
    if room_key == (0, 0, 1):
        for inter_obj in interactive_objects:
            if inter_obj["type"] == "anvil" and player.colliderect(inter_obj["rect"].inflate(50, 50)):
                upgrade_shop_visible = True
                return
    
    # Check for NPCs
    for npc_rect in npcs:
        if player.colliderect(npc_rect.inflate(50, 50)):
            for i, npc in enumerate(room_data.get(room_key, {}).get("npcs", [])):
                # resolve the dynamic state first (if any)
                key = f"{room_key[0]}_{room_key[1]}_{room_key[2]}_{npc.get('id')}_{i}"
                state = npc_states.get(key)
                npc_size = get_npc_size(npc["id"])
                if state:
                    npc_rect_check = pygame.Rect(int(state["x"]), int(state["y"]), npc_size[0], npc_size[1])
                else:
                    npc_rect_check = pygame.Rect(npc["x"], npc["y"], npc_size[0], npc_size[1])

                if npc_rect_check.colliderect(npc_rect):
                    # mark NPC as talking so roaming stops
                    if state is not None:
                        state["talking"] = True

                    if npc["id"] == "knight":
                        if npc.get("rescued", False):
                            dialogue_key = (room_key[0], room_key[1], room_key[2], "knight_rescued")
                        else:
                            dialogue_key = (room_key[0], room_key[1], room_key[2], "knight")

                        if dialogue_key in npc_dialogues:
                            current_dialogue = npc_dialogues[dialogue_key]
                            dialogue_active = True
                            dialogue_index = 0

                            if npc.get("rescued", False) and not quests["rescue_knight"]["complete"]:
                                quests["rescue_knight"]["complete"] = True
                                quests["defeat_goblin_king"]["active"] = True
                                set_message("Knight Rescued!", (0, 255, 0), 2.0)
                    else:
                        # Other NPCs use normal dialogue
                        dialogue_key = (room_key[0], room_key[1], room_key[2], npc["id"])
                        if dialogue_key in npc_dialogues:
                            current_dialogue = npc_dialogues[dialogue_key]
                            dialogue_active = True
                            dialogue_index = 0

                            # Quest completion for elder
                            if npc["id"] == "elder" and not quests["talk_to_elder"]["complete"]:
                                quests["talk_to_elder"]["complete"] = True
                                quests["buy_weapon"]["active"] = True
                                set_message("Quest Updated! Visit the blacksmith.", (0, 255, 0), 2.0)
                            # Special cyber guide in Level 2: give time bandits quest
                            if room_key == (1, 0, 0) and npc.get("id") == "cyber_guide":
                                if not quests.get("kill_time_bandits"):
                                    quests["kill_time_bandits"] = {"active": True, "complete": False, "description": "Eliminate Time Bandits in Neon Streets"}
                                    # start spawns quickly
                                    tb_state = timebandit_rooms.get((1,1,1))
                                    if tb_state:
                                        tb_state["respawn"] = 0.1
                                    set_message("Quest: Kill the Time Bandits in the Neon Streets!", (200, 180, 255), 4.0)
                    return


    for inter_obj in interactive_objects:
        if player.colliderect(inter_obj["rect"].inflate(50, 50)):
            obj_type = inter_obj["type"]
            
            if obj_type == "cage" and room_key == (0, 1, 0):

                room_info = room_data.get(room_key, {})
                knight_rescued = False
                for npc in room_info.get("npcs", []):
                    if npc.get("id") == "knight":
                        knight_rescued = npc.get("rescued", False)
                        break
                
                if not knight_rescued:
                    # Start maze puzzle to rescue knight
                    maze_visible = True
                    maze_player_pos = [1, 1]  # Reset player position
                    maze_completed = False
                    set_message("Solve the maze to free the knight!", (0, 255, 0), 2.0)
                else:
                    set_message("The knight has already been rescued!", (200, 200, 200), 1.5)
            
            elif obj_type == "lever" and room_key == (0, 1, 1):
                if not quests["solve_drawbridge"]["complete"]:
                    quests["solve_drawbridge"]["complete"] = True
                    set_message("Drawbridge Lowered!", (0, 255, 0), 2.0)
            
            elif obj_type == "safe" and room_key == (0, 2, 1):
                if not safe_unlocked:
                    safe_visible = True
                    safe_input = ""
                else:
                    set_message("The safe is already unlocked.", (200, 200, 200), 1.5)
            
            elif obj_type == "portal" and room_key == (0, 2, 2):
                if inventory["Keys"] >= 2:
                    enter_level_2()
                else:
                    need = 2 - inventory["Keys"]
                    set_message(f"You need {need} more key(s) to activate the portal!", (255, 200, 0), 2.0)
            elif obj_type == "datahub" and room_key == (1, 0, 2):
                # Start cipher puzzle (wrapped to avoid crashes)
                try:
                    start_cipher()
                except Exception as e:
                    set_message("Data Hub error: cannot start cipher.", (255, 0, 0), 3.0)
                    print("start_cipher error:", e)
                return
   
    if room_key == (1, 0, 1):  
        for inter_obj in interactive_objects:
            if inter_obj["type"] == "shop" and player.colliderect(inter_obj["rect"].inflate(50, 50)):
                cyber_shop_visible = True
                return

def give_herbs_to_collector():
    """Handle G key to give herbs to the herb collector."""
    global dialogue_active, current_dialogue, dialogue_index
    
    room_key = tuple(current_room)
    if room_key != (0, 2, 1):  # Only in library
        return
    
    # Check if near herb collector
    for npc_rect in npcs:
        if player.colliderect(npc_rect.inflate(50, 50)):
            for npc in room_data.get(room_key, {}).get("npcs", []):
                if npc["id"] == "herbcollector":
                    if inventory["Herbs"] >= 3 and not quests["collect_herbs"]["complete"]:
                        # Give herbs to collector
                        inventory["Herbs"] -= 3
                        quests["collect_herbs"]["complete"] = True
                        
                        # Show special dialogue with code
                        current_dialogue = npc_dialogues[(0, 2, 1, "herbcollector_with_herbs")]
                        dialogue_active = True
                        dialogue_index = 0
                        
                        set_message("You gave 3 herbs to the collector!", (0, 255, 0), 2.0)
                    elif inventory["Herbs"] < 3:
                        set_message("You need 3 herbs to give to the collector!", (255, 200, 0), 1.5)
                    else:
                        set_message("You already gave herbs to the collector.", (200, 200, 200), 1.5)
                    return

def handle_safe_input(number):
    """Handle number input for the safe puzzle."""
    global safe_input, safe_unlocked
    
    if len(safe_input) < 4:
        safe_input += number
        
        if len(safe_input) == 4:
            if safe_input == safe_code:
                safe_unlocked = True
                inventory["Keys"] += 1
                set_message("Safe unlocked! You found a key!", (0, 255, 0), 2.0)
            else:
                safe_input = ""
                set_message("Wrong code! Try again.", (255, 0, 0), 1.5)

#  MAIN GAME LOOP 
running = True
play_button_hover = False
how_to_button_hover = False
about_button_hover = False
back_button_hover = False


boss_initialized = False
boss2_initialized = False

# main loop listens for input updates game state and draws world
while running:
    dt = clock.tick(60)
    keys_pressed = pygame.key.get_pressed()
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.MOUSEMOTION:
            # handle hover states so menus and puzzles feel responsive
            if game_state == "main_menu":
                play_button, how_to_button, about_button = draw_main_menu()
                play_button_hover = play_button.collidepoint(mouse_pos)
                how_to_button_hover = how_to_button.collidepoint(mouse_pos)
                about_button_hover = about_button.collidepoint(mouse_pos)
            elif game_state in ["how_to_play", "about"]:
                back_button = draw_how_to_play() if game_state == "how_to_play" else draw_about()
                back_button_hover = back_button.collidepoint(mouse_pos)
            elif game_state == "playing" and safe_visible:
                buttons, clear_rect, close_rect = draw_safe_puzzle(screen)
            elif game_state == "playing" and maze_visible:
                close_rect = draw_maze_puzzle(screen)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == "main_menu":
                play_button, how_to_button, about_button = draw_main_menu()
                if play_button.collidepoint(mouse_pos):
                    game_state = "playing"
                elif how_to_button.collidepoint(mouse_pos):
                    game_state = "how_to_play"
                elif about_button.collidepoint(mouse_pos):
                    game_state = "about"
            
            elif game_state in ["how_to_play", "about"]:
                back_button = draw_how_to_play() if game_state == "how_to_play" else draw_about()
                if back_button.collidepoint(mouse_pos):
                    game_state = "main_menu"
            
            elif game_state == "playing" and upgrade_shop_visible:
                item_buttons, close_rect = draw_blacksmith_shop(screen)
                
                for button_rect, item_id in item_buttons:
                    if button_rect.collidepoint(mouse_pos):
                        handle_blacksmith_purchase(item_id)
                
                if close_rect.collidepoint(mouse_pos):
                    upgrade_shop_visible = False
            elif game_state == "playing" and cyber_shop_visible:
                item_buttons, close_rect = draw_cyber_shop(screen)
                
                for button_rect, item_id in item_buttons:
                    if button_rect.collidepoint(mouse_pos):
                        handle_cyber_purchase(item_id)
                
                if close_rect.collidepoint(mouse_pos):
                    cyber_shop_visible = False
            
            elif game_state == "playing" and safe_visible:
                buttons, clear_rect, close_rect = draw_safe_puzzle(screen)
                
                # Check number buttons
                for button_rect, number in buttons:
                    if button_rect.collidepoint(mouse_pos):
                        handle_safe_input(number)
                
                # Check clear button
                if clear_rect.collidepoint(mouse_pos):
                    safe_input = ""
                
                # Check close button
                if close_rect.collidepoint(mouse_pos):
                    safe_visible = False
            
            elif game_state == "playing" and maze_visible:
                close_rect = draw_maze_puzzle(screen)
                
                # Check close button
                if close_rect.collidepoint(mouse_pos):
                    maze_visible = False
            elif game_state == "playing" and cipher_visible:
                # compute the same close rect used in draw_cipher_overlay
                box = pygame.Rect(150, 180, 500, 300)
                close_rect = pygame.Rect(box.centerx - 50, box.bottom - 50, 100, 36)
                if close_rect.collidepoint(mouse_pos):
                    cipher_visible = False
        
        elif event.type == pygame.KEYDOWN:
            if game_state == "playing":
                if maze_visible:
                    # arrow keys move through the maze overlay
                    handle_maze_input()
                
                elif cipher_visible:
                    # Delegate cipher key handling to function (safer)
                    try:
                        handle_cipher_key(event)
                    except Exception as e:
                        cipher_visible = False
                        set_message("Data Hub input error.", (255, 0, 0), 2.0)
                        print("handle_cipher_key error:", e)
                
                elif safe_visible:
                    # capture safe code input
                    if event.unicode.isdigit() and len(safe_input) < 4:
                        handle_safe_input(event.unicode)
                    elif event.key == pygame.K_BACKSPACE:
                        safe_input = safe_input[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        safe_visible = False
                
                elif dialogue_active and event.key == pygame.K_SPACE:
                    dialogue_index += 1
                    if dialogue_index >= len(current_dialogue):
                        dialogue_active = False
                        # clear talking flags for all NPCs when dialogue ends
                        for s in npc_states.values():
                            s["talking"] = False
                
                elif upgrade_shop_visible:
                    if event.key == pygame.K_ESCAPE:
                        upgrade_shop_visible = False
                elif cyber_shop_visible:
                    if event.key == pygame.K_ESCAPE:
                        cyber_shop_visible = False
                
                elif event.key == pygame.K_e:
                    hud_visible = not hud_visible
                
                elif event.key == pygame.K_m:
                    map_visible = not map_visible
                
                elif event.key == pygame.K_q:
                    quest_log_visible = not quest_log_visible
                
                elif event.key == pygame.K_h and inventory["Health Potions"] > 0 and health < max_health:
                    inventory["Health Potions"] -= 1
                    health = min(max_health, health + 30)
                    set_message("+30 Health", (0, 255, 0), 1.5)
                
                elif event.key == pygame.K_f:
                    handle_interaction()
                    
                elif event.key == pygame.K_t:
                    enter_level_2()
                
                elif event.key == pygame.K_g:
                    give_herbs_to_collector()
                
               
                elif event.key == pygame.K_SPACE and not upgrade_shop_visible and not dialogue_active and not safe_visible and not maze_visible:
                    if shoot_bullet():
                        set_message("Pew!", (255, 255, 0), 0.5)
                    elif not has_weapon:
                        set_message("You need a weapon! Visit the blacksmith.", (255, 200, 0), 2.0)
                    elif is_reloading:
                        set_message("Reloading...", (255, 200, 0), 0.5)
                    elif ammo == 0:
                        set_message("Out of ammo! Buy more from blacksmith.", (255, 0, 0), 1.0)
                
                
                elif event.key == pygame.K_r and has_weapon and not is_reloading and ammo < max_ammo:
                    # Only allow reload if player has at least one ammo pack
                    if inventory.get("Ammo Packs", 0) > 0:
                        is_reloading = True
                        reload_time = 2.0
                        set_message("Reloading...", (255, 200, 0), 1.0)
                    else:
                        set_message("No ammo packs! Buy some from the blacksmith.", (255, 100, 0), 1.5)
                
                # esc to return to main menu
                elif event.key == pygame.K_ESCAPE and not upgrade_shop_visible and not safe_visible and not maze_visible:
                    game_state = "main_menu"
            
            # Allow ESC to go back from how to play or about screens
            elif event.key == pygame.K_ESCAPE and game_state in ["how_to_play", "about"]:
                game_state = "main_menu"
    
    #
    mouse_x, mouse_y = pygame.mouse.get_pos()
    
    #  SCREEN RENDERING 
    # 
    if game_state == "main_menu":
        play_button, how_to_button, about_button = draw_main_menu()
    
    elif game_state == "how_to_play":
        back_button = draw_how_to_play()
    
    elif game_state == "about":
        back_button = draw_about()
    
    elif game_state == "playing":
        #  GAMEPLAY 
        
        
        if tuple(current_room) == (0, 2, 0) and not boss_initialized:
            init_boss()
            boss_initialized = True
        
        if tuple(current_room) == (1, 2, 2) and not boss2_initialized:
            init_boss2()
            boss2_initialized = True
        

        mv_x = (keys_pressed[pygame.K_d] or keys_pressed[pygame.K_RIGHT]) - (keys_pressed[pygame.K_a] or keys_pressed[pygame.K_LEFT])
        mv_y = (keys_pressed[pygame.K_s] or keys_pressed[pygame.K_DOWN]) - (keys_pressed[pygame.K_w] or keys_pressed[pygame.K_UP])
        
       
        if mouse_x > player.centerx + 10:  
            player_direction = "right"
        elif mouse_x < player.centerx - 10:
            player_direction = "left"
        
        
        if dialogue_active or hud_visible or quest_log_visible or upgrade_shop_visible or safe_visible or maze_visible:
            mv_x, mv_y = 0, 0
        
       
        player_speed_boost_timer = max(0.0, player_speed_boost_timer - (dt / 1000.0))
        player_electrified_timer = max(0.0, player_electrified_timer - (dt / 1000.0))
        
        speed_bonus = 3 if player_speed_boost_timer > 0 else 0
        speed_penalty = 0.5 if player_electrified_timer > 0 else 1.0  # 50% speed reduction when electrified
        
        dx, dy = mv_x * (player_speed + speed_bonus) * speed_penalty, mv_y * (player_speed + speed_bonus) * speed_penalty
        
        # Update enemy movement and NPC roaming before drawing the room
        update_goblins(dt)
        update_timebandits(dt)
        update_npcs(dt)
        
        # Update boss if in throne room
        if tuple(current_room) == (0, 2, 0) and boss and boss["alive"]:
            update_boss(dt)
        # Update AI boss if in AI Control Room
        if tuple(current_room) == (1, 2, 2) and boss2 and boss2.get("alive", False):
            update_boss2(dt)
            check_boss2_hit()
        
        # Draw room
        draw_room(screen, *current_room)
        
        # Movement & collision
        collision_check(dx, dy)
        room_transition()
        
        # Handle damage zones
        handle_damage_zones(dt)
        
        # Check for player death
        if health <= 0:
            respawn_player()
        
        # Collect boss drops
        if tuple(current_room) == (0, 2, 0) and boss_defeated and not boss_drop_collected:
            collect_boss_drops()
        
        # Update weapon systems
        if shoot_cooldown > 0:
            shoot_cooldown = max(0, shoot_cooldown - dt / 1000.0)
        
        if is_reloading:
            reload_time -= dt / 1000.0
            if reload_time <= 0:
                # Consume one ammo pack and refill weapon to max
                if inventory.get("Ammo Packs", 0) > 0:
                    inventory["Ammo Packs"] -= 1
                    ammo = max_ammo
                else:
                    # no packs left; do nothing
                    set_message("Reload failed: no ammo packs.", (255, 100, 0), 1.5)
                is_reloading = False
                reload_time = 0.0
        
        update_bullets(dt)
        
       
        pickup_items()
        
       
        player_moving = (abs(dx) > 0 or abs(dy) > 0)
        draw_player(screen, player, dt, player_moving)
        draw_player_pointer(screen, player)
        
        
        draw_bullets(screen)
        
       
        draw_health_bar(screen)
            
        # Draw UI
        draw_hud(screen) 
        draw_minimap(screen, *current_room)
        draw_quest_log(screen)
        draw_message(screen)
        draw_dialogue(screen)
        draw_blacksmith_shop(screen)
        draw_cyber_shop(screen)
        draw_enhanced_weapon_hud(screen)  


        if hud_visible:
            draw_quick_inventory(screen)
        if DEV_MODE:
            coord_surf = small_font.render(f"{player.x:.0f}, {player.y:.0f}", True, (255, 255, 0))
            screen.blit(coord_surf, (10, ROOM_HEIGHT - 20))
        if safe_visible:
            buttons, clear_rect, close_rect = draw_safe_puzzle(screen)
        
        
        if maze_visible:
            close_rect = draw_maze_puzzle(screen)
        
        if cipher_visible:
            try:
                cipher_close = draw_cipher_overlay(screen)
            except Exception as e:
                cipher_visible = False
                set_message("Error displaying Data Hub.", (255, 0, 0), 3.0)
                print("draw_cipher_overlay error:", e)
        
       
        near_object = False
        for inter_obj in interactive_objects:
            if player.colliderect(inter_obj["rect"].inflate(50, 50)):
                near_object = True
                break
        for npc_rect in npcs:
            if player.colliderect(npc_rect.inflate(50, 50)):
                near_object = True
                break
        
        if near_object and not dialogue_active and not upgrade_shop_visible and not safe_visible and not maze_visible and not cipher_visible:
            hint = small_font.render("Press F to Interact", True, (255, 255, 255))
            screen.blit(hint, (player.centerx - 40, player.top - 25))
            
            # Special hint for herb collector
            room_key = tuple(current_room)
            if room_key == (0, 2, 1):
                for npc in room_data.get(room_key, {}).get("npcs", []):
                    if npc["id"] == "herbcollector" and inventory["Herbs"] >= 3 and not quests["collect_herbs"]["complete"]:
                        give_hint = small_font.render("Press G to Give Herbs", True, (0, 255, 0))
                        screen.blit(give_hint, (player.centerx - 50, player.top - 45))
        
        
        if message_timer > 0:
            message_timer = max(0, message_timer - dt / 1000.0)
    
    pygame.display.flip()

pygame.quit()
