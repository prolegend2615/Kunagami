"""HALLOWSCAPE story content and the authoring validator.

Nodes live in one flat graph. A node belongs to a numbered chapter via its
`chapter` field, which is what gates delayed payoffs and orders Explore Town.
Add prose here; the engine and UI never need to change.
"""

from __future__ import annotations

import re
from typing import Any

from .rules import (
    CHOICE_KEYS,
    DYNAMIC_TARGETS,
    EFFECT_KEYS,
    PAYOFF_KEYS,
    PlayerState,
    matches,
)

ENTRY = "chapter_01"
EMBED_LIMIT = 4000

ITEM_LABELS = {
    "brass_key": "🔑 Brass key",
    "matchbox": "🔥 Blue matchbox",
    "photograph": "📷 Photograph of the house",
    "child_drawing": "🖍️ Child's drawing",
    "phone": "📱 Dead phone",
    "lodging_key": "🗝️ Cellar lodging key",
    "church_key": "⛪ Church key, still warm",
    "name_tag": "🏷️ Paper name tag",
    "menu": "🍽️ Last night's menu",
    "receipt": "🧾 Receipt made out to you",
    "chalk_rubbings": "🖍️ Chalk rubbing of the rules",
    "photograph_pair": "📷 Two photographs of the same street",
}

NPC_LABELS = {
    "stranger": "the stranger in the rain",
    "unknown": "Unknown",
    "watcher": "the Watcher",
    "cook": "the cook",
    "choir": "the church choir",
}

LEDGER_LABELS = {
    "abandoned": "left someone to the town",
    "sheltered": "gave shelter",
    "lingered": "kept looking",
    "named": "gave the town your name",
    "fed": "ate at the town's table",
}

SCARES = {
    "window_flash": "The flash blooms behind the glass.",
    "ground_knock": "A knock answers from under the ground beside you.",
    "wrist": "Something cold closes around your wrist.",
    "behind_you": "It was standing behind you the whole time.",
    "bell": "The church bell rings once, though the tower is empty.",
    "booth": "The thing in the last booth raises a cup to you.",
    "chalk": "Every hand on the chalkboard turns to point at you.",
    "screen": "The screen lights up with tonight, already over.",
}

LOCATIONS = {
    "street": "🏚️ The house across the street",
    "porch": "🚪 The porch",
    "trees": "🌲 The treeline",
    "hall": "🕯️ The hall inside the house",
    "cellar": "🪜 The cellar stair",
    "upstairs": "🛏️ The upstairs rooms",
    "church": "⛪ St. Erth's, where the choir stopped",
    "diner": "☕ The Last Customer, still open",
    "school": "🏫 Hallowscape School, ten minutes late",
}

HUBS = {
    "street": "hub_street",
    "porch": "hub_porch",
    "trees": "hub_trees",
    "hall": "hub_hall",
    "cellar": "hub_cellar",
    "upstairs": "hub_upstairs",
    "church": "hub_church",
    "diner": "hub_diner",
    "school": "hub_school",
}

NODES: dict[str, dict[str, Any]] = {
    "chapter_01": {
        "chapter": 1,
        "location": "street",
        "checkpoint": True,
        "title": "CHAPTER 01 — THE HOUSE ACROSS THE STREET",
        "description": (
            "The road behind you ends at a wall of black trees. Your phone reads "
            "**October 31, 11:59 PM**—then the screen goes dark.\n\n"
            "Across the street, the abandoned house has one lit window. A figure "
            "stands behind it, perfectly still.\n\n"
            "Your phone vibrates. No signal. One new message from **Unknown**:\n"
            "*\"Don't let it know you're awake.\"*\n\n"
            "The porch light flickers. The front door is open a few inches."
        ),
        "echoes": [
            {
                "when": {"previous_runs": ">=1"},
                "text": "*You have stood in this road before. Your feet already know which plank of the porch gives.*",
            }
        ],
        "choices": [
            {
                "id": "watch_window",
                "label": "👁️ Watch the Window",
                "next": "window",
                "watcher": 1,
                "ledger": {"lingered": 1},
                "clue": "The figure in the lit window never blinks. When the porch light flashes, its reflection is missing.",
            },
            {
                "id": "cross_street",
                "label": "🏚️ Cross to the House",
                "next": "porch",
                "item": "brass_key",
                "clue": "A brass key lies in the wet leaves. The prints around it face the house—and stop at the curb.",
            },
            {
                "id": "reply_unknown",
                "label": "📱 Reply to Unknown",
                "next": "message",
                "flag": "answered_unknown",
                "watcher": 1,
                "clue": 'You type: WHO ARE YOU? The reply arrives before you send it: *"You, if you open the door."*',
            },
            {
                "id": "run_trees",
                "label": "🌲 Run for the Trees",
                "next": "trees",
                "flag": "entered_trees",
                "clue": "The trees are closer than they looked. Something walks between them at your pace.",
            },
        ],
    },
    "window": {
        "chapter": 1,
        "location": "street",
        "title": "CHAPTER 01 — THE WINDOW",
        "description": (
            "You hold your breath and watch the lit window. The figure's head turns—not toward you, "
            "but toward the empty street behind you.\n\n"
            "A second phone lights up inside the house. Its screen shows a photograph of **you**, "
            "standing exactly where you are now.\n\nFrom somewhere nearby, a floorboard creaks."
        ),
        "choices": [
            {
                "id": "approach_window",
                "label": "🪟 Get a Closer Look",
                "next": "after_window",
                "scare": "window_flash",
                "watcher": 1,
                "item": "photograph",
                "clue": "The photograph inside is dated tomorrow.",
            },
            {
                "id": "hide_window",
                "label": "🌑 Hide in the Ditch",
                "next": "after_hide",
                "flag": "hid_from_watcher",
                "watcher": -1,
            },
        ],
    },
    "porch": {
        "chapter": 1,
        "location": "porch",
        "title": "CHAPTER 01 — THE PORCH",
        "description": (
            "The brass key is cold enough to sting. You step onto the porch. The door swings inward "
            "by itself.\n\nIn the dark hall, a telephone rings once. Then a voice from upstairs "
            "whispers your name.\n\nBehind you, at the bottom of the steps, someone is breathing. "
            "A stranger in a rain-soaked coat won't look at the house. *\"Let me past you,\"* they "
            "say. *\"Please. It only takes what answers the door.\"*"
        ),
        "choices": [
            {
                "id": "use_brass_key",
                "label": "🔑 Try the Key",
                "requires_item": "brass_key",
                "next": "after_key",
                "item": "child_drawing",
                "scare": "ground_knock",
                "clue": "The key opens a small locked drawer. Inside is a child's drawing of this house, with you at the window.",
            },
            {"id": "shelter_stranger", "label": "🤝 Pull Them Onto the Porch", "next": "stranger_shelter"},
            {"id": "refuse_stranger", "label": "🚪 Slip Inside First", "next": "stranger_refuse"},
            {"id": "leave_porch", "label": "↩️ Step Away", "next": "after_leave"},
        ],
    },
    "stranger_shelter": {
        "chapter": 1,
        "location": "porch",
        "title": "CHAPTER 01 — TWO ON THE STEPS",
        "description": (
            "You haul them up onto the porch. The breathing stops. Whatever was doing it walks "
            "past the steps without once turning a head.\n\n*\"It counted us,\"* the stranger "
            "whispers. *\"Two of us. It only takes one.\"*\n\nThe front door is still open. "
            "Warm light spills out of it, and for the first time tonight that looks like bait."
        ),
        "choices": [
            {
                "id": "enter_together",
                "label": "🚪 Go In Together",
                "next": "after_leave",
                "flag": "saved_stranger",
                "relation": {"stranger": 2},
                "ledger": {"sheltered": 1},
                "clue": "The stranger's name is Wren. They know the house took someone in October, and never says which October.",
            },
            {
                "id": "leave_wren",
                "label": "🏃 Leave Them on the Porch",
                "next": "after_leave",
                "flag": "sin:left_wren",
                "relation": {"stranger": -2},
                "ledger": {"abandoned": 1},
                "watcher": 1,
                "clue": "You take three steps. Behind you, the porch is empty. No footsteps followed.",
            },
        ],
    },
    "stranger_refuse": {
        "chapter": 1,
        "location": "porch",
        "title": "CHAPTER 01 — THE DOOR CLOSES",
        "description": (
            "You duck through the doorway and let it shut. The lock turns by itself.\n\n"
            "Through the wood, the stranger says your name—*your name*, which you never gave. "
            "Then the knocks start. Three of them. Slow.\n\nThe voice from upstairs answers: "
            "*\"You can come in when you're ready. They can't.\"*"
        ),
        "choices": [
            {
                "id": "open_door_again",
                "label": "🔑 Unlock It Again",
                "requires_item": "brass_key",
                "next": "after_leave",
                "flag": "tried_to_open",
                "watcher": -1,
                "hide_if_locked": True,
            },
            {
                "id": "walk_away_hall",
                "label": "🕯️ Walk Into the Hall",
                "next": "after_leave",
                "flag": "sin:left_at_door",
                "relation": {"stranger": -2},
                "ledger": {"abandoned": 1, "lingered": 1},
                "clue": "Three knocks. Then the sound of rain starting and stopping, as if someone were being carried.",
            },
        ],
    },
    "message": {
        "chapter": 1,
        "location": "street",
        "title": "CHAPTER 01 — THE REPLY",
        "description": (
            "The typing indicator appears. It stays there for almost a minute.\n\n"
            "**Unknown:** *\"You already know. Look at the house.\"*\n\nThe figure is no longer in "
            'the window. Your phone buzzes again: *"It saw the screen light up."*'
        ),
        "choices": [
            {
                "id": "follow_message",
                "label": "📨 Ask What It Wants",
                "next": "after_message",
                "flag": "pressed_unknown",
                "watcher": 1,
                "ledger": {"lingered": 1},
                "clue": 'Unknown: *"It wants the person holding the phone."*',
            },
            {"id": "put_phone_away", "label": "📵 Turn Off the Phone", "next": "after_phone_off", "watcher": -1},
        ],
    },
    "trees": {
        "chapter": 1,
        "location": "trees",
        "title": "CHAPTER 01 — THE TREELINE",
        "description": (
            "You run. The trees swallow the road noise. Your shoes splash through mud, but a "
            "second set of footsteps keeps pace just behind you.\n\nA matchbox sits on a stump. "
            "One match is already burning, though there is no wind."
        ),
        "choices": [
            {
                "id": "take_match",
                "label": "🔥 Take the Match",
                "next": "after_match",
                "item": "matchbox",
                "scare": "wrist",
                "watcher": 1,
                "clue": "The match burns blue. In its light, the footprints beside yours are bare.",
            },
            {"id": "return_road", "label": "🏃 Run Back to the Road", "next": "after_trees"},
        ],
    },
    "after_window": {
        "chapter": 1,
        "location": "street",
        "title": "CHAPTER 01 — THE PHOTOGRAPH",
        "description": (
            "For one bright instant, the figure is standing behind you in the reflection.\n\n"
            "When you turn, the street is empty. The house's front door is now wide open, and the "
            "porch light has gone out."
        ),
        "choices": [
            {"id": "enter_house", "label": "🚪 Enter the House", "next": "hall"},
            {
                "id": "search_leaves_window",
                "label": "🍂 Search the Wet Leaves",
                "next": "hall",
                "item": "brass_key",
                "watcher": 1,
                "clue": "Under the leaves: a brass key, and a second photograph of the same street taken ten years apart.",
            },
        ],
    },
    "after_hide": {
        "chapter": 1,
        "location": "street",
        "title": "CHAPTER 01 — HOLD STILL",
        "description": (
            "You crouch in the ditch. Across the street, the figure presses one palm against the "
            "window. A slow, deliberate knock answers from beneath the ground beside you.\n\nThe "
            "front door stands open."
        ),
        "choices": [
            {"id": "go_to_door", "label": "🚪 Go to the Door", "next": "hall", "watcher": 1},
            {
                "id": "listen_ground",
                "label": "👂 Press Your Ear to the Soil",
                "next": "hall",
                "watcher": 2,
                "flag": "heard_underneath",
                "clue": "Under the road, someone is knocking in threes. It keeps count, and it is one short.",
            },
        ],
    },
    "after_key": {
        "chapter": 1,
        "location": "porch",
        "title": "CHAPTER 01 — THE DRAWING",
        "description": (
            "The child's drawing is signed with your initials. On the back, someone has written: "
            "*\"The house remembers who came in.\"*\n\nA door upstairs clicks open. At the bottom "
            "of the steps the stranger is still waiting, and now there is a second shape beside "
            "them that has no face at all."
        ),
        "choices": [
            {"id": "warn_stranger", "label": "🗣️ Warn the Stranger", "next": "hall", "flag": "saved_stranger", "relation": {"stranger": 1}, "ledger": {"sheltered": 1}},
            {"id": "go_upstairs", "label": "🪜 Go Inside", "next": "hall", "ledger": {"lingered": 1}},
        ],
    },
    "after_leave": {
        "chapter": 1,
        "location": "hall",
        "title": "CHAPTER 01 — THE CALL",
        "description": (
            "The door shuts gently behind you. The telephone rings again, this time from your "
            'pocket. Your phone screen is black, but a voice speaks through it: *"You came in. We '
            'kept the door open anyway."*'
        ),
        "choices": [
            {"id": "answer_call", "label": "📱 Answer", "next": "hall", "watcher": 1},
            {
                "id": "let_it_ring",
                "label": "🔇 Let It Ring Out",
                "next": "hall",
                "watcher": -1,
                "flag": "ignored_the_call",
                "clue": "It rings eleven times. On the twelfth, the hall light comes on by itself.",
            },
        ],
    },
    "after_message": {
        "chapter": 1,
        "location": "street",
        "title": "CHAPTER 01 — TYPING",
        "description": (
            'Unknown: *"Leave the phone on the road and come inside."*\n\nThe figure reappears in '
            "the window, holding a phone of its own. Your screen shows the same conversation from "
            "its side."
        ),
        "choices": [
            {"id": "enter_house_2", "label": "🏚️ Go to the House", "next": "hall"},
            {
                "id": "leave_phone_road",
                "label": "📵 Leave the Phone on the Road",
                "next": "hall",
                "flag": "left_phone",
                "watcher": -1,
                "clue": "You set it down screen-up. By the time you reach the curb, the screen is dark and the call log reads: ME.",
            },
        ],
    },
    "after_phone_off": {
        "chapter": 1,
        "location": "street",
        "title": "CHAPTER 01 — NO SIGNAL",
        "description": (
            "The phone shuts off. In the quiet you hear footsteps on the other side of the street. "
            "They stop just behind the front door. So do yours, a half-second too late."
        ),
        "choices": [
            {"id": "enter_house_3", "label": "🚪 Open the Door", "next": "hall", "watcher": 1},
            {
                "id": "count_breaths",
                "label": "🫁 Count Its Breaths",
                "next": "hall",
                "watcher": 2,
                "flag": "counted_breaths",
                "clue": "It breathes in threes, the same rhythm as the knocking. When you stop counting, it stops too.",
            },
        ],
    },
    "after_match": {
        "chapter": 1,
        "location": "trees",
        "title": "CHAPTER 01 — BLUE FLAME",
        "description": (
            "The flame gutters out. In the mud, a trail of wet footprints leads back to the house. "
            "None lead away. Something barefoot has been standing at the edge of the trees, "
            "watching you watch the light."
        ),
        "choices": [
            {"id": "follow_footprints", "label": "👣 Follow the Prints", "next": "hall", "watcher": 1},
            {
                "id": "match_own_feet",
                "label": "🦶 Compare Them to Your Own",
                "next": "hall",
                "watcher": 2,
                "flag": "prints_matched",
                "clue": "The bare prints are your size, your walk, and they start where you stopped standing.",
            },
        ],
    },
    "after_trees": {
        "chapter": 1,
        "location": "street",
        "title": "CHAPTER 01 — THE ROAD",
        "description": (
            "The road is waiting, exactly as you left it. Behind the house's lit window, the figure "
            "raises one hand and points at the open front door. The porch light comes on for you, "
            "like a dog called in from the cold."
        ),
        "choices": [
            {"id": "enter_house_4", "label": "🏚️ Go to the House", "next": "hall"},
            {
                "id": "wave_back",
                "label": "👋 Wave at the Window",
                "next": "hall",
                "watcher": 3,
                "flag": "waved_at_watcher",
                "scare": "window_flash",
                "clue": "It waves back with both hands. It does not have both hands.",
            },
        ],
    },
    "hall": {
        "chapter": 2,
        "location": "hall",
        "checkpoint": True,
        "title": "CHAPTER 02 — THE HALL",
        "description": (
            "The hall smells of wet wool and old smoke. Everything in this house is arranged for a "
            "family that left in a hurry: four chairs, one pulled back, a coat still on the hook.\n\n"
            "The wallpaper pattern is photographs. Dozens of them, and every one has the same person "
            "standing in the road outside."
        ),
        "variants": [
            {
                "when": {"has_flags": ["hid_from_watcher"]},
                "text": "*You hid from it in the ditch, and it still let you in. That is the part you can't stop thinking about.*",
            },
            {
                "when": {"has_flags": ["entered_trees"]},
                "text": "*Your shoes are still muddy from the treeline. The mud on the hall floor is not yours.*",
            },
            {
                "when": {"has_items": ["brass_key"]},
                "text": "*The brass key is warm in your pocket, warmer than the room.*",
            },
            {
                "when": {"has_flags": ["answered_unknown"]},
                "text": '*Unknown writes one more time, on a phone with no signal: *"You came in faster than the last one."*',
            },
        ],
        "choices": [
            {
                "id": "go_cellar",
                "label": "🪜 Follow the Cold",
                "next": "cellar",
                "clue": "The cellar stair breathes cold air in a rhythm. In. Out. In.",
            },
            {
                "id": "examine_wall",
                "label": "🖼️ Study the Wallpaper",
                "next": "hall_wall",
                "watcher": 1,
                "ledger": {"lingered": 1},
                "clue": "Every photograph is the same street, the same night, a different stranger.",
            },
            {
                "id": "examine_photo",
                "label": "📷 Compare Your Photograph",
                "requires_item": "photograph",
                "next": "hall_wall",
                "hide_if_locked": True,
                "clue": "Your photograph is already in the wallpaper. It was taken before you arrived.",
            },
            {"id": "go_upstairs", "label": "🛏️ Take the Stairs", "next": "bedroom_door"},
        ],
    },
    "hall_wall": {
        "chapter": 2,
        "location": "hall",
        "title": "CHAPTER 02 — THE WALL",
        "description": (
            "You count the strangers in the paper. Then you count again, because the number has "
            "changed. One frame is empty and its glass is warm.\n\nUnder the smallest frame, a "
            "child's handwriting: *\"THE HOUSE REMEMBERS WHO CAME IN.\"*"
        ),
        "choices": [
            {"id": "take_frame", "label": "🖼️ Pry Out the Empty Frame", "next": "bedroom_door", "item": "lodging_key", "clue": "Behind the empty frame: a lodging key and a date that has not happened yet."},
            {"id": "back_away_wall", "label": "↩️ Back Away", "next": "bedroom_door", "watcher": -1},
        ],
    },
    "cellar": {
        "chapter": 2,
        "location": "cellar",
        "title": "CHAPTER 02 — THE CELLAR",
        "description": (
            "Twelve steps down, and you have counted them twice with the same answer: thirteen. "
            "The cold is deliberate, like a hand held to your mouth.\n\nSomeone has been living "
            "here. A bedroll, a tin cup, and the walls scratched with tally marks—grouped in "
            "threes."
        ),
        "lines": [
            {
                "when": {"ledger": {"abandoned": ">=1"}},
                "text": "On the bedroll lies a coat soaked through with rain, and a face you turned away from at the door.",
            }
        ],
        "choices": [
            {"id": "read_scratches", "label": "🔍 Read the Scratches", "next": "bedroom_door", "watcher": 1, "clue": "The last tally is not a mark. It is your initials."},
            {"id": "climb_out", "label": "🪜 Climb Back Up", "next": "bedroom_door", "watcher": -1},
        ],
    },
    "bedroom_door": {
        "chapter": 2,
        "location": "upstairs",
        "checkpoint": True,
        "title": "CHAPTER 02 — THE KNOCKING",
        "description": (
            "You hear three knocks from inside your bedroom closet.\n\nYou're certain you locked it "
            "before going to sleep.\n\nThe knocking stops.\n\nThen your Discord notification "
            'sounds.\n\n**Unknown:** *"Don\'t open it. I\'m inside."*\n\nThe closet door has a '
            "lock on the outside. The hallway window is open onto the dark."
        ),
        "variants": [
            {"when": {"relation": {"stranger": ">=1"}}, "text": "*Somewhere below you a door that you opened is being closed by someone else.*"},
            {"when": {"watcher_at_least": 4}, "text": "*You are not alone on this landing, and this time you can hear it breathing.*"},
        ],
        "scare": "behind_you",
        "choices": [
            {"id": "open_closet", "label": "🚪 Open the Closet", "next": "ending_first_light", "watcher": 2, "clue": "The closet is empty except for a phone, still recording, propped to face the door."},
            {
                "id": "use_key_closet",
                "label": "🗝️ Lock It from Outside",
                "requires_item": "lodging_key",
                "next": "ending_locked",
            },
            {"id": "leave_room", "label": "🪟 Go Out the Window", "next": "street_again", "watcher": -1},
        ],
    },
    "ending_first_light": {
        "chapter": 2,
        "location": "upstairs",
        "title": "CHAPTER 02 — THE FIRST LIGHT",
        "ending": "taken",
        "description": (
            "The closet is empty. The phone on the floor is still recording, and it is pointed at "
            "the door—at you.\n\nBehind you the room goes bright, though there is no lamp lit in "
            "this house. The last thing on the recording is your own voice saying a name you don't "
            "remember learning.\n\n**The town keeps what it takes.**\n\n*Your journal, your debts, "
            "and the choices you made stay in Hallowscape. If you come back to the road, it will "
            "already know which plank gives.*"
        ),
        "choices": [],
    },
    "ending_locked": {
        "chapter": 2,
        "location": "upstairs",
        "title": "CHAPTER 02 — THE OTHER SIDE",
        "ending": "lodger",
        "description": (
            "The lodging key turns. Something inside says *thank you* in your mother's voice, and "
            "goes quiet.\n\nYou sleep on the landing with your back to the door, and in the morning "
            "the house has one more photograph in its wallpaper: you, asleep, taken from inside the "
            "closet.\n\n**You are the town's lodger now.** The cellar has your bedroll ready."
        ),
        "choices": [],
    },
    # ---------------------------------------------------------------- CHAPTER 03
    "street_again": {
        "chapter": 3,
        "location": "street",
        "checkpoint": True,
        "title": "CHAPTER 03 — THE STREET THAT WASN'T",
        "description": (
            "You go out through the window and land in the wet leaves where you found the key.\n\n"
            "The house across the street is dark and boarded, as if nobody had opened it for "
            "years. Your phone has four bars and one unread message, sent tonight by your own "
            'number: *"See you October 31."*\n\nThree blocks away, a church is the only light left '
            "in town. A notice board faces the road."
        ),
        "variants": [
            {
                "when": {"has_any": ["sin:left_wren", "sin:left_at_door"]},
                "text": "*Your shoes are wet on one foot only. The other print in the leaves belongs to someone you left behind.*",
            },
            {
                "when": {"has_flags": ["saved_stranger"]},
                "text": "*There are two sets of prints in the leaves now, and both came from the house.*",
            },
        ],
        "choices": [
            {"id": "check_house", "label": "🏚️ Go Back to the House", "next": "house_dark", "watcher": 1},
            {"id": "walk_light", "label": "⛪ Walk Toward the Light", "next": "church_yard"},
            {
                "id": "read_notice",
                "label": "📜 Read the Notice Board",
                "next": "church_notice",
                "clue": "SERVICES 10 MINUTES LATE. The word LATE is underlined so hard the paper tore.",
            },
        ],
    },
    "house_dark": {
        "chapter": 3,
        "location": "street",
        "title": "CHAPTER 03 — THE OPEN HOUSE",
        "description": (
            "The front door is gone. Not broken—gone, with the frame painted over, as if the house "
            "decided it never had one.\n\nInside, the wallpaper is the same photograph pattern, but "
            "every frame on it is empty. On the hall table a cup of coffee sits, still warm."
        ),
        "choices": [
            {
                "id": "pocket_photo",
                "label": "📷 Pocket One Empty Frame",
                "next": "church_yard",
                "item": "photograph_pair",
                "watcher": 1,
                "clue": "The empty frame has tape on the back labelled with tonight's date and your name in someone else's handwriting.",
            },
            {"id": "leave_house", "label": "⛪ Leave for the Church", "next": "church_yard", "watcher": -1},
            {
                "id": "drink_coffee",
                "label": "☕ Drink the Coffee",
                "next": "church_yard",
                "ledger": {"fed": 1},
                "watcher": 2,
                "clue": "It tastes of the diner on Route 9, which closed before you were born.",
            },
        ],
    },
    "church_notice": {
        "chapter": 3,
        "location": "street",
        "title": "CHAPTER 03 — THE ROLL",
        "description": (
            "Beneath the service notice someone has pinned a roll of names, one per October, in "
            "different hands. The list is short. The last line is fresh ink.\n\nIt is your name, "
            "{name}, written in your own handwriting."
        ),
        "choices": [
            {
                "id": "tear_roll",
                "label": "📋 Tear Off Your Line",
                "next": "church_yard",
                "item": "name_tag",
                "flag": "denied_the_roll",
                "watcher": 1,
                "clue": "The page underneath is a photograph of you reading this page.",
            },
            {
                "id": "leave_roll",
                "label": "⛪ Leave It Written",
                "next": "church_yard",
                "flag": "accepted_the_roll",
                "watcher": -1,
            },
        ],
    },
    "church_yard": {
        "chapter": 3,
        "location": "church",
        "checkpoint": True,
        "title": "CHAPTER 03 — THE YARD",
        "description": (
            "St. Erth's has no steeple; the bells were sold for the roof, the roof for the heating, "
            "and the heating for something else. The door is open and warm.\n\nIn the yard, the "
            "graves face the church like an audience. One of them is open, freshly dug, and covered "
            "with a plank that has not been used yet."
        ),
        "choices": [
            {
                "id": "read_stones",
                "label": "🪦 Read the Stones",
                "next": "church_graves",
                "clue": "Every death date is October 31. Every age is the age you are now.",
            },
            {"id": "enter_nave", "label": "🚪 Go Inside", "next": "church_nave"},
            {
                "id": "cover_grave",
                "label": "🪵 Set the Plank Properly",
                "next": "church_nave",
                "watcher": -1,
                "ledger": {"sheltered": 1},
                "flag": "covered_the_grave",
            },
        ],
    },
    "church_graves": {
        "chapter": 3,
        "location": "church",
        "title": "CHAPTER 03 — THE CONGREGATION",
        "description": (
            "You read until your mouth goes dry. Forty-one of them, all in the last hundred years, "
            "all taken on the same night. At the end of the row the newest stone is already carved, "
            "and it is only waiting for a date.\n\nBehind you, the open grave is no longer empty. "
            "Something is lying in it, comfortably, looking up at the sky."
        ),
        "choices": [
            {
                "id": "look_in",
                "label": "🕳️ Look Down at It",
                "next": "church_nave",
                "scare": "bell",
                "watcher": 2,
                "flag": "saw_own_grave",
                "clue": "It has no face, but it has your coat, and your hands, and it is wearing your watch.",
            },
            {"id": "back_to_yard", "label": "↩️ Step Back", "next": "church_nave", "watcher": -1},
        ],
    },
    "church_nave": {
        "chapter": 3,
        "location": "church",
        "checkpoint": True,
        "title": "CHAPTER 03 — THE STOPPED CHOIR",
        "description": (
            "The pews are full of people in rain coats, all facing forward, none of them breathing "
            "the way a crowd should. Up front the choir stands with mouths open, frozen mid-note, "
            "thirty seconds from a hymn that began decades ago.\n\nThe parson turns from the altar. "
            "He has your phone number written on his palm. The collection plate comes toward you."
        ),
        "variants": [
            {
                "when": {"has_flags": ["covered_the_grave"]},
                "text": "*The plank you set over the grave has been carried in and laid on the altar like a shroud. Someone approves.*",
            },
            {
                "when": {"relation": {"stranger": ">=2"}},
                "text": "*In the third pew there is a stranger in a rain-soaked coat, saved and dry, holding the hymn book open to your name.*",
            },
        ],
        "choices": [
            {
                "id": "give_name",
                "label": "🗣️ Say Your Name into the Plate",
                "next": "vestry",
                "flag": "gave_name",
                "ledger": {"named": 1},
                "item": "name_tag",
                "watcher": 2,
                "clue": "The plate is a photograph. Your name goes in, and the choir moves one note closer to finishing.",
            },
            {"id": "keep_silent", "label": "🤫 Keep Your Mouth Shut", "next": "vestry", "relation": {"choir": -1}, "watcher": -1},
            {"id": "out_vestry", "label": "🚪 Past into the Vestry", "next": "vestry"},
        ],
    },
    "vestry": {
        "chapter": 3,
        "location": "church",
        "title": "CHAPTER 03 — THE GUEST LEDGER",
        "description": (
            "The vestry smells of wax and wet wool. The parson's guest ledger lies open, and it is "
            "not a book of visitors—it is a book of *lodgers*, each entry a name, an October, and a "
            "single word for how they left.\n\nThe word used most often, in many hands, is STAYED. "
            "The last blank line is ruled for you."
        ),
        "choices": [
            {
                "id": "read_ledger",
                "label": "📖 Read Every Entry",
                "next": "diner_park",
                "watcher": 1,
                "ledger": {"lingered": 1},
                "clue": "One entry says WREN — STAYED — and the ink is old enough to be true.",
            },
            {"id": "take_key", "label": "🗝️ Take the Church Key", "next": "diner_park", "item": "church_key", "flag": "took_the_key"},
            {
                "id": "sign_line",
                "label": "✍️ Write Yourself In",
                "next": "diner_park",
                "flag": "listed_lodger",
                "ledger": {"named": 1},
                "watcher": 2,
                "clue": "You write STAYED under your own name, and the pen is warm afterward, as if someone else had been holding it.",
            },
        ],
    },
    # ---------------------------------------------------------------- CHAPTER 04
    "diner_park": {
        "chapter": 4,
        "location": "diner",
        "checkpoint": True,
        "title": "CHAPTER 04 — THE LAST CUSTOMER",
        "description": (
            "Route 9 has one neon sign left alive: THE LAST CUSTOMER, OPEN. It is not open. The "
            "door unlocks anyway.\n\nThe cook stands with his back to the room at the grill. In the "
            "far booth sits a figure in a wet coat, one cup raised in a slow toast, and the coffee "
            "in it is still moving."
        ),
        "variants": [
            {
                "when": {"has_flags": ["gave_name"]},
                "text": "The jukebox plays and sings your name in the chorus, and nobody in town taught it that.",
            },
            {
                "when": {"watcher_at_least": 5},
                "text": "*The figure in the booth has stood up. It has been standing up for a while.*",
            },
        ],
        "choices": [
            {"id": "sit_counter", "label": "🍽️ Sit at the Counter", "next": "counter"},
            {"id": "order_coffee", "label": "☕ Order Coffee", "next": "coffee", "ledger": {"fed": 1}},
            {"id": "to_booth", "label": "🪑 Approach the Booth", "next": "booth", "watcher": 2, "scare": "booth"},
        ],
    },
    "counter": {
        "chapter": 4,
        "location": "diner",
        "title": "CHAPTER 04 — THE MENU",
        "description": (
            "The laminated menu lists no food. It lists names, and beside each one a number of "
            "years—how long they held out before they stayed. The prices are all one night.\n\nThe "
            "cook's back does not move, but a mug turns around in front of you."
        ),
        "choices": [
            {
                "id": "study_menu",
                "label": "📖 Study the Menu",
                "next": "cook_turn",
                "item": "menu",
                "watcher": 1,
                "ledger": {"lingered": 1},
                "clue": "Wren's entry reads 0 YEARS. They never left the porch.",
            },
            {"id": "ring_bell", "label": "🔔 Ring for Service", "next": "cook_turn", "watcher": 1},
            {"id": "leave_diner", "label": "🚪 Walk Out to the Road", "next": "road_back", "watcher": -1},
        ],
    },
    "coffee": {
        "chapter": 4,
        "location": "diner",
        "title": "CHAPTER 04 — FULL OF RAIN",
        "description": (
            "The coffee arrives before you finish ordering. It is not coffee. It is the rain from "
            "the night you came, kept warm in a cup, and it is exactly the amount that fell.\n\n"
            "Drinking it would be accepting a plate at this table. The town counts that."
        ),
        "choices": [
            {
                "id": "drink",
                "label": "🥄 Drink It",
                "next": "cook_turn",
                "ledger": {"fed": 1},
                "watcher": 1,
                "flag": "ate_at_the_table",
                "clue": "The rain goes down like something you already had. The cook relaxes.",
            },
            {"id": "pour_out", "label": "🚽 Pour It into the Sink", "next": "cook_turn", "relation": {"cook": -2}, "watcher": -1},
            {
                "id": "tip",
                "label": "💵 Leave a Tip for Wren",
                "next": "cook_turn",
                "ledger": {"sheltered": 1},
                "relation": {"stranger": 1},
                "flag": "paid_for_wren",
            },
        ],
    },
    "booth": {
        "chapter": 4,
        "location": "diner",
        "title": "CHAPTER 04 — THE LAST BOOTH",
        "description": (
            "You cross the checkered floor. Up close the figure in the booth has no face and every "
            "face; it wears your coat, your watch, and your phone in its hand with the screen up.\n\n"
            "The screen shows this conversation, typed by you, sent two minutes before you arrive."
        ),
        "choices": [
            {
                "id": "sit_booth",
                "label": "🪑 Sit Down Opposite It",
                "next": "cook_turn",
                "watcher": 3,
                "flag": "sat_with_watcher",
                "clue": "It slides a second cup across. The rim is warm where its mouth was.",
            },
            {
                "id": "grab_phone",
                "label": "📱 Take Your Phone Back",
                "next": "cook_turn",
                "watcher": 2,
                "item": "phone",
                "flag": "reclaimed_phone",
            },
            {"id": "back_away", "label": "↩️ Back Away Slowly", "next": "counter", "watcher": -1},
        ],
    },
    "cook_turn": {
        "chapter": 4,
        "location": "diner",
        "checkpoint": True,
        "title": "CHAPTER 04 — THE COOK TURNS AROUND",
        "description": (
            "The cook turns. It is the stranger from the porch, apron on over a coat still soaked "
            "through, and their face is fine—*your* face is fine, that's the problem. They smile "
            "with your mouth.\n\n*\"Kitchen's closed,\"* they say, in your voice. *\"I can let you "
            "out the back. You have to leave somebody a name, though. Rules.\"*"
        ),
        "variants": [
            {
                "when": {"relation": {"stranger": ">=2"}},
                "text": "*They keep looking at you like someone who was let in out of the rain once, a long time ago, and remembers it.*",
            },
            {
                "when": {"ledger": {"abandoned": ">=1"}},
                "text": "*They have your hands and they use them to lock the back door before they speak.*",
            },
        ],
        "choices": [
            {
                "id": "give_surname",
                "label": "🗝️ Leave Them Your Name",
                "next": "road_back",
                "flag": "gave_name",
                "ledger": {"named": 1},
                "relation": {"cook": 2},
                "watcher": 1,
                "clue": "You trade names at a counter in a closed diner. Their face gets better. Yours gets less certain.",
            },
            {
                "id": "refuse_cook",
                "label": "🙅 Refuse to Trade",
                "next": "road_back",
                "relation": {"cook": -2},
                "watcher": 2,
                "flag": "refused_the_cook",
            },
            {"id": "ask_wants", "label": "🗣️ Ask What It Wants", "next": "ask_wants", "watcher": 1, "ledger": {"lingered": 1}},
        ],
    },
    "ask_wants": {
        "chapter": 4,
        "location": "diner",
        "title": "CHAPTER 04 — WHAT IT WANTS",
        "description": (
            '*The cook wipes their hands on the apron. *"The same thing it always wants: someone to '
            'hold the phone. It goes dead, you go in, the town gets its night back."*\n\nThey nod at '
            "the booth where your phone sits with four bars and one bar and no bars, draining.\n\n"
            '*\"Give it yours and it has to use that one instead. It\'s a fair trade. It\'s the only '
            'trade.\"*'
        ),
        "choices": [
            {
                "id": "hand_over",
                "label": "📱 Hand It Your Phone",
                "next": "road_back",
                "flag": "gave_phone",
                "watcher": -2,
                "relation": {"watcher": 1},
                "clue": "You give it the phone you arrived with. The screen shows a photo of this diner, taken from the road, tonight.",
            },
            {"id": "keep_phone", "label": "🔌 Keep It", "next": "road_back", "flag": "kept_phone", "watcher": 2, "item": "phone"},
        ],
    },
    "road_back": {
        "chapter": 4,
        "location": "street",
        "title": "CHAPTER 04 — THE ONLY ROAD LEFT",
        "description": (
            "Out front, Route 9 has narrowed to one lane and then to a sidewalk. Every house you "
            "pass is dark and warm, lit from inside like a room someone just left.\n\nAt the end of "
            "it, a school: HALLOWSCAPE COUNTY, and a bell that has already rung. The field is full "
            "of children standing perfectly still, all of them facing the door you have to use."
        ),
        "choices": [
            {
                "id": "to_school",
                "label": "🏫 Go to the School",
                "next": "school_gate",
                "clue": "Attendance is taken every ten minutes. Nobody has ever been late enough to be marked.",
            },
            {
                "id": "hide_field",
                "label": "🌾 Cross the Field to Them",
                "next": "school_gate",
                "watcher": 2,
                "flag": "walked_among_children",
                "scare": "chalk",
            },
        ],
    },
    # ---------------------------------------------------------------- CHAPTER 05
    "school_gate": {
        "chapter": 5,
        "location": "school",
        "checkpoint": True,
        "title": "CHAPTER 05 — TEN MINUTES LATE",
        "description": (
            "The corridor smells of chalk and wet coats. Every clock in the building reads 11:59, "
            "and every one of them is ten minutes slow.\n\nIn the first classroom a chalkboard is "
            "covered in the town's rules, written and rewritten by hundreds of different hands. The "
            "last rule is fresh, in handwriting you recognise as your own."
        ),
        "variants": [
            {
                "when": {"has_flags": ["gave_name"]},
                "text": "*The roll call on the desk has your name on it, and next to it, in the second column, a tick already made.*",
            },
            {
                "when": {"has_flags": ["gave_phone"]},
                "text": "*Somewhere in this building a phone you no longer own is ringing, patient, waiting for you to answer it.*",
            },
        ],
        "choices": [
            {"id": "classroom", "label": "🏫 Enter the Classroom", "next": "classroom"},
            {
                "id": "copy_rules",
                "label": "🖍️ Copy the Last Rule",
                "next": "classroom",
                "item": "chalk_rubbings",
                "watcher": 1,
                "clue": "DON'T LET IT KNOW YOU'RE AWAKE. Under it, newer: DON'T LET IT KNOW YOU LEFT.",
            },
            {"id": "hall_names", "label": "📷 Follow the Photograph Wall", "next": "hall_of_names"},
        ],
    },
    "classroom": {
        "chapter": 5,
        "location": "school",
        "checkpoint": True,
        "title": "CHAPTER 05 — ROLL CALL",
        "description": (
            "Twenty desks, all occupied, all by children who stopped moving a long time ago. The "
            "teacher at the front has her back turned, holding a roll of names, and she begins to "
            "read them in October order.\n\nShe reaches your name. The room stops writing."
        ),
        "choices": [
            {
                "id": "answer_roll",
                "label": "🙋 Answer to {name}",
                "next": "hall_of_names",
                "flag": "answered_roll",
                "watcher": 2,
                "ledger": {"named": 1},
                "clue": "Here. You said here. The teacher makes a mark and the mark is wet.",
            },
            {
                "id": "stay_quiet",
                "label": "🤫 Stay Quiet",
                "next": "hall_of_names",
                "watcher": -1,
                "flag": "went_unanswered",
                "relation": {"watcher": -1},
            },
            {
                "id": "answer_wrong",
                "label": "🎭 Answer with Wren's Name",
                "next": "hall_of_names",
                "requires_item": "name_tag",
                "hide_if_locked": True,
                "flag": "answered_as_wren",
                "watcher": 1,
                "relation": {"stranger": 2},
                "ledger": {"sheltered": 1},
            },
        ],
    },
    "hall_of_names": {
        "chapter": 5,
        "location": "school",
        "title": "CHAPTER 05 — THE HALL OF NAMES",
        "description": (
            "The hall is lined with framed photographs of every class this town ever taught. In "
            "each one, at the back, standing where the light doesn't reach, is the same adult "
            "figure—the Watcher, in a different coat each decade, always holding a phone.\n\nThe "
            "final frame is empty and warm, and the auditorium doors at the end of the hall are "
            "open, and full of applause."
        ),
        "variants": [
            {
                "when": {"has_any": ["faced_watcher", "sat_with_watcher"]},
                "text": "*In every frame it is looking at the camera. In the newest ones it is looking at you looking at it.*",
            },
        ],
        "choices": [
            {"id": "to_auditorium", "label": "👏 Go In to the Applause", "next": "auditorium"},
            {
                "id": "search_wren",
                "label": "🔍 Find Wren's Class",
                "next": "auditorium",
                "watcher": 1,
                "ledger": {"lingered": 1},
                "clue": "Wren's class photo has them standing in the back row where the Watcher usually stands, holding the phone, still.",
            },
            {
                "id": "pry_frame",
                "label": "🖼️ Take the Empty Frame",
                "next": "auditorium",
                "item": "photograph_pair",
                "watcher": 2,
                "flag": "took_the_frame",
            },
        ],
    },
    "auditorium": {
        "chapter": 5,
        "location": "school",
        "checkpoint": True,
        "title": "CHAPTER 05 — HALLOWSCAPE",
        "description": (
            "The whole town is here, in the seats, in their coats, applauding at exactly the speed "
            "of a recording. On the stage a lamp is lit, and under it stands the Watcher holding a "
            "phone with no signal, facing all of them, waiting for the one person still awake.\n\n"
            "It says, in your voice, into a microphone that is off: *\"Last chance to be "
            "somewhere else.\"*"
        ),
        "variants": [
            {
                "when": {"relation": {"stranger": ">=2"}},
                "text": "*In the front row a stranger in a dry coat stands up, and holds out a hand toward the aisle, and waits to see whether you take it.*",
            },
            {
                "when": {"ledger": {"abandoned": ">=1"}},
                "text": "*In the front row something you left at a door is sitting very comfortably, saving your seat.*",
            },
        ],
        "choices": [
            {
                "id": "walk_out",
                "label": "🚪 Walk Out into the October Dark",
                "next": "ending_escape",
                "when": {"lacks_flags": ["gave_name"]},
            },
            {
                "id": "stay_wren",
                "label": "🤝 Take Wren's Hand",
                "next": "ending_stayed",
                "when": {"relation": {"stranger": ">=2"}},
                "style": "success",
            },
            {"id": "stay_seat", "label": "🪑 Sit Down with the Town", "next": "ending_stayed_seat"},
            {
                "id": "take_stage",
                "label": "🎭 Go Up and Take the Lamp",
                "next": "ending_replace",
                "when": {"watcher_at_least": 6},
                "style": "danger",
            },
        ],
    },
    "ending_escape": {
        "chapter": 5,
        "location": "school",
        "title": "CHAPTER 05 — SOMEWHERE ELSE",
        "ending": "gone",
        "description": (
            "You walk out. Nobody turns, which is somehow the worst of it.\n\nThe road is a "
            "sidewalk, the sidewalk is a lane, Route 9 is Route 9, and by sunrise you are in a "
            "petrol station forty miles from anywhere with four bars and a photograph in your "
            "pocket that shows a person standing in a road, taken from inside a house.\n\n**You "
            "never gave them your name, so the town never quite finished writing you.** It will "
            "leave the porch light on, in case."
        ),
        "choices": [],
    },
    "ending_stayed": {
        "chapter": 5,
        "location": "school",
        "title": "CHAPTER 05 — TWO OUT OF THE RAIN",
        "ending": "together",
        "description": (
            "You take the hand. It is cold and it is solid and it holds.\n\nThe applause does not "
            "stop, but the doors are open now, and the two of you walk down the aisle of a town "
            "that has learned to look at its laps. Outside, the road has come back.\n\n**Two of you "
            "leave Hallowscape. That is one more than it ever allowed.** Somewhere behind you, in "
            "the front row, the stranger's seat stays empty, and the town keeps it empty, out of "
            "spite."
        ),
        "choices": [],
    },
    "ending_stayed_seat": {
        "chapter": 5,
        "location": "school",
        "title": "CHAPTER 05 — A PLACE IN THE ROW",
        "ending": "stayed",
        "description": (
            "You sit. The coat around you is warm and it fits before you put it on.\n\nIn the "
            "morning the teacher takes the roll again and reads your name in October order, and "
            "somewhere in a town you used to live in, a family finds one more frame on the hallway "
            "wall: a class photo, back row, standing where the light doesn't reach, holding a "
            "phone.\n\n**You stayed. The word is used in many hands.**"
        ),
        "choices": [],
    },
    "ending_replace": {
        "chapter": 5,
        "location": "school",
        "title": "CHAPTER 05 — UNDER THE LAMP",
        "ending": "watcher",
        "description": (
            "You go up and take the lamp. The phone in your hand has no signal and every message "
            "ever sent to it, and the whole town turns to look at the person holding it.\n\nIt is "
            "ten minutes to midnight, and it will be, for you, for a very long time. In the front "
            "row a stranger in a wet coat is just arriving, and you know exactly what to tell "
            'them.\n\n*"Don\'t let it know you\'re awake."*\n\n**You are the Watcher now, and the '
            "town remembers everything you did before you had this face.**"
        ),
        "choices": [],
    },
    # ---------------------------------------------------------------- HUBS (Explore Town)
    "hub_street": {
        "chapter": 1,
        "location": "street",
        "hub": True,
        "title": "EXPLORE — THE ROAD",
        "description": (
            "You come back down the road to where you first stood that night. The wall of black "
            "trees is where you left it, and the house is whichever state you last saw it in.\n\n"
            "The porch light is on. It is always on when you come back here."
        ),
        "choices": [
            {
                "id": "street_look",
                "label": "👁️ Stand and Watch",
                "next": "hub_street",
                "watcher": 1,
                "clue": "From the road the lit window is at the height of a standing person on the second floor. There is no second floor.",
            },
            {"id": "street_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint", "watcher": -1},
        ],
    },
    "hub_porch": {
        "chapter": 1,
        "location": "porch",
        "hub": True,
        "title": "EXPLORE — THE PORCH",
        "description": "The steps give at the same plank. The leaves under the key's spot have been turned over, recently, by something with no hands.",
        "choices": [
            {"id": "porch_knock", "label": "✊ Knock on the Door", "next": "hub_porch", "watcher": 2, "scare": "ground_knock"},
            {
                "id": "porch_sit",
                "label": "🪑 Sit on the Steps",
                "next": "hub_porch",
                "ledger": {"lingered": 1},
                "clue": "Two sets of prints in the frost. One comes to the steps. Neither leaves.",
            },
            {"id": "porch_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint", "watcher": -1},
        ],
    },
    "hub_trees": {
        "chapter": 1,
        "location": "trees",
        "hub": True,
        "title": "EXPLORE — THE TREELINE",
        "description": "The trees keep their own weather. The stump where the matchbox sat has been cut fresh, and the rings count eleven.",
        "choices": [
            {
                "id": "trees_walk",
                "label": "🌲 Walk In",
                "next": "hub_trees",
                "watcher": 2,
                "flag": "went_deeper",
                "clue": "Eleven rings, eleven winters. This wood was standing sixty years ago.",
            },
            {"id": "trees_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint", "watcher": -1},
        ],
    },
    "hub_hall": {
        "chapter": 2,
        "location": "hall",
        "hub": True,
        "title": "EXPLORE — THE HALL",
        "description": "The four chairs are arranged the same way, and the fourth is pulled out a little further than you left it. The coat on the hook is now your size.",
        "choices": [
            {
                "id": "hall_count",
                "label": "🖼️ Count the Frames Again",
                "next": "hub_hall",
                "watcher": 1,
                "ledger": {"lingered": 1},
                "clue": "Forty-one frames. One more than last time you counted, and it is not empty anymore.",
            },
            {"id": "hall_coat", "label": "🧥 Touch the Coat", "next": "hub_hall", "watcher": 1},
            {"id": "hall_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint", "watcher": -1},
        ],
    },
    "hub_cellar": {
        "chapter": 2,
        "location": "cellar",
        "hub": True,
        "title": "EXPLORE — THE CELLAR",
        "description": "Thirteen steps, counted twice. The cold still breathes. The bedroll has been slept in since you were down here.",
        "choices": [
            {
                "id": "cellar_tally",
                "label": "🔢 Add Your Own Tally",
                "next": "hub_cellar",
                "flag": "marked_the_wall",
                "watcher": 1,
                "clue": "You scratch three marks. Under your nails there is chalk that was not there before.",
            },
            {"id": "cellar_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint", "watcher": -1},
        ],
    },
    "hub_upstairs": {
        "chapter": 2,
        "location": "upstairs",
        "hub": True,
        "title": "EXPLORE — THE LANDING",
        "description": "The closet door is shut and the hallway window is open onto nothing in particular. The room is warm in a way that means someone has been sitting here.",
        "choices": [
            {
                "id": "listen_closet",
                "label": "👂 Listen at the Closet",
                "next": "hub_upstairs",
                "watcher": 2,
                "clue": "Inside, something is breathing in threes and keeping count.",
            },
            {"id": "upstairs_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint", "watcher": -1},
        ],
    },
    "hub_church": {
        "chapter": 3,
        "location": "church",
        "hub": True,
        "title": "EXPLORE — ST. ERTH'S",
        "description": "The choir is still thirty seconds from finishing. The collection plate has been emptied and refilled with rain.",
        "choices": [
            {
                "id": "church_pew",
                "label": "🙏 Sit in a Pew",
                "next": "hub_church",
                "watcher": -1,
                "ledger": {"sheltered": 1},
                "clue": "Sitting down here is the closest thing this town offers to being safe.",
            },
            {"id": "church_bell", "label": "🔔 Pull the Bell Rope", "next": "hub_church", "scare": "bell", "watcher": 2, "flag": "rang_the_bell"},
            {"id": "church_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint"},
        ],
    },
    "hub_diner": {
        "chapter": 4,
        "location": "diner",
        "hub": True,
        "title": "EXPLORE — THE LAST CUSTOMER",
        "description": "The neon still says OPEN. The booth in the back has two cups out now, and one of them has someone's lipstick on the rim.",
        "choices": [
            {
                "id": "diner_grill",
                "label": "🍳 Check the Grill",
                "next": "hub_diner",
                "watcher": 1,
                "clue": "The grill is cold and the coffee pot is full and warm, and there is no flame under anything.",
            },
            {"id": "diner_jukebox", "label": "🎵 Play the Jukebox", "next": "hub_diner", "watcher": 1, "ledger": {"lingered": 1}},
            {"id": "diner_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint"},
        ],
    },
    "hub_school": {
        "chapter": 5,
        "location": "school",
        "hub": True,
        "title": "EXPLORE — HALLOWSCAPE SCHOOL",
        "description": "Every clock reads 11:59, ten minutes slow, in a building with no power. The corridor is lined with coats by size, and this year's row has a gap with your name on the hook.",
        "choices": [
            {
                "id": "school_board",
                "label": "🖍️ Rewrite the Rules",
                "next": "hub_school",
                "flag": "wrote_a_rule",
                "watcher": 2,
                "clue": "You add one line to the board. When you turn back, three children have copied it.",
            },
            {"id": "school_back", "label": "🕯️ Return to Your Story", "next": "@checkpoint"},
        ],
    },
}


# The town remembers: declarative consequences, evaluated when the player
# reaches `chapter`/`after_chapter`. Content can queue a payoff without code.
PAYOFFS: list[dict[str, Any]] = [
    {
        "id": "wren_waits_upstairs",
        "when": {"has_flags": ["saved_stranger"]},
        "chapter": "hall",
        "line": "*The stranger you pulled onto the porch is already inside. They are standing at the far end of the hall, pointing upstairs, and they cannot make a sound.*",
        "choices": [
            {
                "id": "follow_wren",
                "label": "🤝 Follow Wren Upstairs",
                "next": "bedroom_door",
                "relation": {"stranger": 1},
                "watcher": -1,
                "clue": "Wren's hand is cold and solid. Someone is holding it from the other side.",
            }
        ],
        "once": True,
    },
    {
        "id": "abandoned_photograph",
        "when": {"has_any": ["sin:left_wren", "sin:left_at_door"]},
        "chapter": "hall",
        "scare": "ground_knock",
        "line": "There is a fresh photograph face-down on the hall table. It shows the front door from the outside, and someone is still knocking on it.",
        "choices": [
            {
                "id": "open_for_them",
                "label": "🚪 Open the Door for Them",
                "next": "cellar",
                "relation": {"stranger": 2},
                "ledger": {"abandoned": -1, "sheltered": 1},
                "flag": "paid_the_debt",
                "clue": "You open it for a stranger in a rain-soaked coat. They thank you by name and step past you into the house.",
                "watcher": 1,
            },
            {
                "id": "keep_photograph",
                "label": "📷 Keep the Photograph",
                "next": "hall",
                "item": "photograph",
                "watcher": 1,
                "clue": "The photograph of the door has your handwriting on the back: LET ME IN.",
            },
        ],
        "once": True,
    },
    {
        "id": "watcher_arrives",
        "when": {"watcher_at_least": 4},
        "chapter": "bedroom_door",
        "scare": "behind_you",
        "line": "*You kept looking. It kept coming. The breathing on the landing has stopped being pretend.*",
        "choices": [
            {
                "id": "face_watcher",
                "label": "👁️ Turn and Face It",
                "next": "ending_first_light",
                "flag": "faced_watcher",
                "watcher": 2,
                "clue": "It has no face, but it has your phone number, and it says it like a name.",
            }
        ],
        "once": True,
    },
    {
        "id": "debt_collector",
        "when": {"ledger": {"abandoned": ">=1"}},
        "after_chapter": "hall",
        "chapter": "cellar",
        "queue_event": {
            "kind": "town_change",
            "text": "The porch light is off now. You left it on.",
            "due_in": 1800,
            "flag": "town_darkened",
        },
        "once": True,
    },
    # ---- Chapter 03
    {
        "id": "wren_lights_a_candle",
        "when": {"has_flags": ["saved_stranger"]},
        "chapter": "church_yard",
        "line": "*Someone has already lit a candle here, in the wind, and it is burning down toward your name rather than away from it.*",
        "choices": [
            {
                "id": "candle_for_wren",
                "label": "🕯️ Light a Second Candle",
                "next": "church_nave",
                "relation": {"stranger": 1},
                "ledger": {"sheltered": 1},
                "watcher": -1,
                "flag": "lit_for_wren",
                "clue": "Two candles in a church with no congregation. The town cannot decide which one you are.",
            }
        ],
        "once": True,
    },
    {
        "id": "debt_follows_to_the_yard",
        "when": {"has_any": ["sin:left_wren", "sin:left_at_door"]},
        "chapter": "church_yard",
        "scare": "ground_knock",
        "line": "The open grave has been covered while you were not looking. There are knock marks on the underside of the plank.",
        "choices": [
            {
                "id": "ask_forgiveness",
                "label": "🙏 Ask the Grave's Forgiveness",
                "next": "church_nave",
                "flag": "paid_the_debt",
                "relation": {"stranger": 2},
                "ledger": {"abandoned": -1, "sheltered": 1},
                "watcher": -2,
                "clue": "You say sorry into a hole in the ground. The plank warms under your hands, once, like a door being opened from the other side.",
            }
        ],
        "once": True,
    },
    {
        "id": "choir_remembers_the_refusal",
        "when": {"relation": {"choir": "<=1"}},
        "chapter": "vestry",
        "line": "*Thirty seconds of hymn, held for decades. The choir has started turning their heads toward the vestry while you read.*",
        "queue_event": {
            "kind": "town_change",
            "text": "The church bell rang at three, though nobody was in the tower.",
            "due_in": 3600,
            "flag": "bell_rang_for_you",
        },
        "once": True,
    },
    # ---- Chapter 04
    {
        "id": "phone_on_the_grill",
        "when": {"has_flags": ["gave_phone"]},
        "chapter": "counter",
        "scare": "screen",
        "line": "Your phone is on the counter, charging, and it has a call waiting from a number that is this diner's.",
        "choices": [
            {
                "id": "answer_diner_phone",
                "label": "📞 Answer It",
                "next": "cook_turn",
                "flag": "answered_it",
                "watcher": 2,
                "item": "receipt",
                "clue": "The caller is you, from a year that has not happened, and you sound relieved.",
            }
        ],
        "once": True,
    },
    {
        "id": "the_table_knows_you",
        "when": {"ledger": {"fed": ">=2"}},
        "chapter": "cook_turn",
        "line": "*The cook has already set your place. Twice now, at two different tables, in a town that keeps no cutlery for the dead.*",
        "choices": [
            {
                "id": "ask_for_seconds",
                "label": "🍽️ Ask for Seconds",
                "next": "road_back",
                "ledger": {"fed": 1},
                "relation": {"cook": 1},
                "watcher": -1,
                "flag": "guest_of_the_town",
                "clue": "Eating here twice makes you a guest. Guests get a door held open. That is the whole of the kindness on offer.",
            }
        ],
        "once": True,
    },
    {
        "id": "wren_paid_the_tip",
        "when": {"has_flags": ["paid_for_wren"]},
        "chapter": "cook_turn",
        "line": "*On the tip jar there is a note in your handwriting thanking you for something you have not done yet.*",
        "once": True,
    },
    # ---- Chapter 05
    {
        "id": "frame_from_last_time",
        "when": {"previous_runs": ">=1"},
        "chapter": "hall_of_names",
        "line": "*One of the older frames is a class photo you have never seen in your life, and the back of it is written in your hand: I WAS THE ONE WHO LEFT.*",
        "once": True,
    },
    {
        "id": "wren_took_your_place",
        "when": {"has_flags": ["answered_as_wren"]},
        "chapter": "hall_of_names",
        "line": "The register on the wall has been updated. WREN is marked GONE, in wet ink, and under it your name is marked STAYED. That is what a trade costs here.",
        "relation": {"stranger": -3},
        "ledger": {"abandoned": 1},
        "scare": "chalk",
        "once": True,
    },
    {
        "id": "keeper_offers_the_coat",
        "when": {"watcher_at_least": 5},
        "chapter": "hall_of_names",
        "choices": [
            {
                "id": "try_the_coat",
                "label": "🧥 Try the Coat on the Hook",
                "next": "auditorium",
                "flag": "wore_the_coat",
                "watcher": 2,
                "clue": "It fits, it is warm, and when you turn around the hall of photographs has rearranged itself to put you in every one.",
            }
        ],
        "once": True,
    },
    {
        "id": "children_unlocked",
        "when": {"has_flags": ["freed_children"]},
        "chapter": "auditorium",
        "line": "*The classroom doors are open behind you. Twenty coats hang empty on their hooks, and the applause in here has begun to sound like rain on a roof.*",
        "choices": [
            {
                "id": "walk_out_class",
                "label": "🚪 Walk Out with the Class",
                "next": "ending_stayed",
                "style": "success",
            }
        ],
        "once": True,
    },
    {
        "id": "unnamed_exit",
        "when": {"has_flags": ["went_unanswered"]},
        "chapter": "auditorium",
        "line": "*The teacher never marked you. Somewhere in this building your name is still blank on the roll, and a blank name can walk out of a room.*",
        "once": True,
    },
]

# What the town does on its own, while nobody is looking. The clock draws from
# these, and `when` decides which line a given player deserves.
TOWN_EVENTS: list[dict[str, Any]] = [
    {"text": "The porch light is on again. Nobody walked up to it.", "kind": "town_change"},
    {"text": "It rained at three. Only on the road in front of your house.", "kind": "weather"},
    {"text": "A knock, in threes, kept count while you were away.", "kind": "knock"},
    {
        "when": {"ledger": {"abandoned": ">=1"}},
        "text": "Someone stood at your door for a long time and then stopped standing there.",
        "kind": "debt",
        "flag": "they_came_back",
    },
    {
        "when": {"has_flags": ["saved_stranger"]},
        "text": "A candle was lit somewhere in town, and it burned down without going out.",
        "kind": "bond",
        "flag": "candle_kept",
    },
    {
        "when": {"has_flags": ["saved_stranger"]},
        "text": "Somebody said {name} at the church door and stopped as soon as it was heard.",
        "kind": "bond",
    },
    {
        "when": {"watcher_at_least": 3},
        "text": "The Watcher moved closer while you slept. It is now in the house rather than across it.",
        "kind": "watcher",
        "flag": "watcher_moved_in",
    },
    {
        "when": {"watcher_at_least": 6},
        "text": "You were not alone in the room you left. Nothing took anything. It only watched you leave.",
        "kind": "watcher",
        "flag": "it_was_inside",
    },
    {
        "when": {"has_flags": ["gave_name"]},
        "text": "The notice board has been rewritten. Your name is in the fresh ink, twice.",
        "kind": "roll",
        "flag": "roll_updated",
    },
    {
        "when": {"has_items": ["brass_key"]},
        "text": "Every locked door in town has been opened once and closed again, in your absence.",
        "kind": "town_change",
    },
    {"text": "The diner sign buzzed all night with nobody in it.", "kind": "town_change"},
    {"text": "School let out ten minutes late, as always, and the field emptied anyway.", "kind": "town_change"},
    {"text": "Your phone lit up with a message and then remembered it had no signal.", "kind": "phone"},
]

LINE_KEYS = {"when", "text"}
VARIANT_KEYS = {"when", "text"}
NODE_KEYS = {
    "chapter",
    "location",
    "checkpoint",
    "hub",
    "title",
    "description",
    "variants",
    "lines",
    "echoes",
    "choices",
    "scare",
    "ending",
    "unlocks",
}


def chapter_order() -> dict[str, int]:
    return {node_id: int(node.get("chapter", 0)) for node_id, node in NODES.items()}


def validate() -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for the whole story graph."""
    errors: list[str] = []
    warnings: list[str] = []
    probe = PlayerState(chapter=ENTRY)

    if ENTRY not in NODES:
        errors.append(f"ENTRY '{ENTRY}' is not a node.")

    for node_id, node in NODES.items():
        unknown = set(node) - NODE_KEYS
        if unknown:
            errors.append(f"{node_id}: unknown node keys {sorted(unknown)}")
        if node.get("location") not in LOCATIONS:
            errors.append(f"{node_id}: location {node.get('location')!r} is not in LOCATIONS")
        if not node.get("title"):
            errors.append(f"{node_id}: missing title")
        if not node.get("description"):
            errors.append(f"{node_id}: missing description")

        # Pessimistic embed budget: base text plus every optional line.
        budget = len(node.get("description", "")) + sum(
            len(entry.get("text", "")) for key in ("variants", "lines", "echoes") for entry in node.get(key, [])
        )
        if budget > EMBED_LIMIT:
            errors.append(f"{node_id}: text can reach {budget} chars, over the {EMBED_LIMIT} embed limit")
        elif budget > EMBED_LIMIT - 400:
            warnings.append(f"{node_id}: text can reach {budget} chars — leave room for payoffs")

        optional = {"variants", "lines", "echoes"}
        for key in optional:
            for i, entry in enumerate(node.get(key, [])):
                bad = set(entry) - LINE_KEYS
                if bad:
                    errors.append(f"{node_id}: {key}[{i}] has unknown keys {sorted(bad)}")
                if not entry.get("text"):
                    errors.append(f"{node_id}: {key}[{i}] has no text")
                try:
                    matches(entry.get("when"), probe)
                except ValueError as exc:
                    errors.append(f"{node_id}: {key}[{i}] bad predicate — {exc}")
                if key == "variants" and not entry.get("when"):
                    errors.append(f"{node_id}: {key}[{i}] has no 'when', so the variant is dead weight")

        if node.get("scare") and node["scare"] not in SCARES:
            errors.append(f"{node_id}: scare tag {node['scare']!r} is not in SCARES")

        choices = node.get("choices", [])
        if node.get("ending") and choices:
            errors.append(f"{node_id}: ending nodes must have no choices")
        if not node.get("ending") and not choices:
            errors.append(f"{node_id}: dead end with no choices and no 'ending'")
        if len(choices) == 1:
            warnings.append(f"{node_id}: single-choice node reads as a slideshow — merge it or add an action")
        if len(choices) > 8:
            errors.append(f"{node_id}: {len(choices)} choices exceeds the usable button layout")

        seen: set[str] = set()
        for choice in choices:
            bad = set(choice) - CHOICE_KEYS
            if bad:
                errors.append(f"{node_id}/{choice.get('id')}: unknown choice keys {sorted(bad)}")
            cid = choice.get("id")
            if not cid:
                errors.append(f"{node_id}: choice without id: {choice}")
                continue
            if cid in seen:
                errors.append(f"{node_id}: duplicate choice id '{cid}'")
            seen.add(cid)
            if not choice.get("label"):
                errors.append(f"{node_id}/{cid}: missing label")
            if len(str(choice.get("label", ""))) > 55:
                errors.append(f"{node_id}/{cid}: label over Discord's 80-char cap or unreadable")
            target = choice.get("next")
            if target not in NODES and target not in DYNAMIC_TARGETS:
                errors.append(f"{node_id}/{cid}: next '{target}' is not a node")
            if target == "@checkpoint" and not node.get("hub"):
                errors.append(f"{node_id}/{cid}: only hub nodes may travel to @checkpoint")
            for item in ([choice["requires_item"]] if choice.get("requires_item") else choice.get("requires_items", [])):
                if item not in ITEM_LABELS:
                    errors.append(f"{node_id}/{cid}: requires unknown item {item!r}")
                elif not _obtainable_before(item, node_id):
                    errors.append(f"{node_id}/{cid}: requires {item!r}, but nothing grantable before it can give it")
            for group, table in (("item", ITEM_LABELS), ("items", ITEM_LABELS)):
                for item in choice.get(group, []) if group == "items" else []:
                    if item not in table:
                        errors.append(f"{node_id}/{cid}: grants unknown item {item!r}")
            if choice.get("item") and choice["item"] not in ITEM_LABELS:
                errors.append(f"{node_id}/{cid}: grants unknown item {choice['item']!r}")
            for npc in choice.get("relation", {}):
                if npc not in NPC_LABELS:
                    errors.append(f"{node_id}/{cid}: relation to unknown NPC {npc!r}")
            for tag in choice.get("ledger", {}):
                if tag not in LEDGER_LABELS:
                    errors.append(f"{node_id}/{cid}: ledger tag {tag!r} is not in LEDGER_LABELS")
            if choice.get("scare") and choice["scare"] not in SCARES:
                errors.append(f"{node_id}/{cid}: scare tag {choice['scare']!r} is not in SCARES")
            try:
                matches(choice.get("when"), probe)
            except ValueError as exc:
                errors.append(f"{node_id}/{cid}: bad predicate — {exc}")
            for event in [choice.get("queue_event"), *choice.get("queue_events", [])]:
                if event and not event.get("text"):
                    errors.append(f"{node_id}/{cid}: queued event has no text")
        if node.get("hub") and not any(c.get("next") == "@checkpoint" for c in choices):
            errors.append(f"{node_id}: hub node has no choice that returns to the story")

    _validate_reachability(errors)
    _validate_payoffs(errors, warnings, probe)
    _validate_town_events(errors, probe)
    return errors, warnings


def _validate_town_events(errors: list[str], probe: PlayerState) -> None:
    """The offline clock reads these, so a bad entry would surface as a crash in a DM."""
    if not TOWN_EVENTS:
        errors.append("TOWN_EVENTS is empty — nothing would ever happen while players are away")
    for i, event in enumerate(TOWN_EVENTS):
        bad = set(event) - {"when", "text", "kind", "flag"}
        if bad:
            errors.append(f"TOWN_EVENTS[{i}]: unknown keys {sorted(bad)}")
        if not event.get("text"):
            errors.append(f"TOWN_EVENTS[{i}]: no text")
        if len(str(event.get("text", ""))) > 300:
            errors.append(f"TOWN_EVENTS[{i}]: text too long to send as a one-line memory")
        try:
            matches(event.get("when"), probe)
        except ValueError as exc:
            errors.append(f"TOWN_EVENTS[{i}]: bad predicate — {exc}")
    unconditional = [event for event in TOWN_EVENTS if not event.get("when")]
    if len(unconditional) < 3:
        errors.append("fewer than three town events apply to everyone — idle players would get silence")


def _edges_ignore_predicates(node_id: str) -> list[str]:
    out = []
    for choice in NODES[node_id].get("choices", []):
        if choice.get("next") in NODES:
            out.append(choice["next"])
    return out


def _can_reach(start: str, target: str, seen: set[str] | None = None) -> bool:
    seen = seen or set()
    if start == target:
        return True
    if start in seen:
        return False
    seen.add(start)
    return any(_can_reach(nxt, target, seen) for nxt in _edges_ignore_predicates(start))


def _reachable_from_entry() -> set[str]:
    out: set[str] = set()
    stack = [ENTRY]
    while stack:
        node_id = stack.pop()
        if node_id not in NODES or node_id in out:
            continue
        out.add(node_id)
        stack.extend(_edges_ignore_predicates(node_id))
    for rule in PAYOFFS:
        for choice in rule.get("choices", []):
            if choice.get("next") in NODES and rule.get("chapter") in out:
                stack.append(choice["next"])
                while stack:
                    node_id = stack.pop()
                    if node_id not in NODES or node_id in out:
                        continue
                    out.add(node_id)
                    stack.extend(_edges_ignore_predicates(node_id))
    return out


def _obtainable_before(item: str, at_node: str) -> bool:
    """Is `item` grantable on some path that can still reach `at_node`?"""
    for node_id, node in NODES.items():
        if not _can_reach(node_id, at_node):
            continue
        for choice in node.get("choices", []):
            granted = [choice["item"]] if choice.get("item") else choice.get("items", [])
            if item in granted and _can_reach(ENTRY, node_id):
                return True
    return False


def _validate_reachability(errors: list[str]) -> None:
    reachable = _reachable_from_entry()
    for node_id, node in NODES.items():
        if node.get("hub"):
            continue
        if node_id not in reachable:
            errors.append(f"{node_id}: unreachable from ENTRY (ignoring predicates)")
    endings = [n for n, node in NODES.items() if node.get("ending")]
    if not endings:
        errors.append("no ending nodes — the story cannot be completed or echoed")
    for location, hub in HUBS.items():
        node = NODES.get(hub)
        if node is None:
            errors.append(f"HUBS[{location!r}] points at missing node {hub!r}")
        elif not node.get("hub"):
            errors.append(f"{hub}: listed in HUBS but has no 'hub': True")
        elif node.get("location") != location:
            errors.append(f"{hub}: listed as the {location!r} hub but its location is {node.get('location')!r}")
    for node_id, node in NODES.items():
        if node.get("hub") and node_id not in HUBS.values():
            errors.append(f"{node_id}: marked 'hub' but no location routes to it")


def _validate_payoffs(errors: list[str], warnings: list[str], probe: PlayerState) -> None:
    seen: set[str] = set()
    order = chapter_order()
    for rule in PAYOFFS:
        rid = rule.get("id")
        if not rid:
            errors.append("payoff without id")
            continue
        bad = set(rule) - PAYOFF_KEYS
        if bad:
            errors.append(f"payoff {rid}: unknown keys {sorted(bad)}")
        if rid in seen:
            errors.append(f"payoff {rid}: duplicate id")
        seen.add(rid)
        target = rule.get("chapter")
        if target not in NODES:
            errors.append(f"payoff {rid}: chapter target {target!r} is not a node")
        if "after_chapter" in rule:
            gate = rule["after_chapter"]
            if gate not in NODES:
                errors.append(f"payoff {rid}: after_chapter {gate!r} is not a node")
            elif gate == target:
                errors.append(f"payoff {rid}: after_chapter cannot be its own target")
            elif not _can_reach(gate, target):
                errors.append(f"payoff {rid}: {target!r} is never reachable after {gate!r}")
        try:
            matches(rule.get("when"), probe)
        except ValueError as exc:
            errors.append(f"payoff {rid}: bad predicate — {exc}")
        if not any(rule.get(key) for key in ("line", "scare", "choices", "replace_text", *EFFECT_KEYS)):
            errors.append(f"payoff {rid}: has no effect")
        for choice in rule.get("choices", []):
            bad_target = choice.get("next") not in NODES and choice.get("next") not in DYNAMIC_TARGETS
            if bad_target:
                errors.append(f"payoff {rid}/{choice.get('id')}: next {choice.get('next')!r} is not a node")
            if choice.get("payoff"):
                errors.append(f"payoff {rid}/{choice.get('id')}: 'payoff' key is reserved by the engine")
            if not choice.get("id") or not choice.get("label"):
                errors.append(f"payoff {rid}: injected choice needs an id and a label: {choice}")
        if not rule.get("when"):
            warnings.append(f"payoff {rid}: no 'when', fires every time the chapter is reached")
