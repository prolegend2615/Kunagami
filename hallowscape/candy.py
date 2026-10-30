"""The Candy Door — the mini-game where the town knocks at your door.

Five nights. Children arrive at a porch light. Some of them are children. The
rule card is the only weapon: a visitor is unsafe if it visibly breaks a rule
that is printed on tonight's card, and the tell for every break is either in the
description or in the answer to a question the player can ask. Nothing is
unguessable, and no real child ever breaks a stated rule.

Rules and consequences are separated from the Discord UI on purpose: the numbers
below are what the validator asserts, and `validate_door()` is what stops a bad
night from shipping.
"""

from __future__ import annotations

from typing import Any

from . import story

NIGHTS_TOTAL = 5
START_HEARTS = 3
START_REPUTATION = 100
START_CANDY = 3
SUPPLY_PER_NIGHT = 2

REP_GIVE_REAL = 5
REP_DENY_REAL = -10
REP_GIVE_ANOMALY = -15
HEART_COST = -1

REPUTATION_CAP = 100

# --------------------------------------------------------------------------- rules
# Each card line states something a player can physically check from a doorway.
RULES = {
    "shadow": "Real children throw a shadow in the porch light. Nothing that stands in the light without one is standing there.",
    "teeth": "A child's grin has gaps in it. If the smile is full and every tooth is the same size, it is not their smile.",
    "door": "They come for candy. They do not come for the door. Anything that asks to be invited in is not here for sweets.",
    "breath": "It is four degrees out and the road is wet. Real children breathe. Watch the air in front of the mouth.",
    "costume": "The drowned-girl costume was banned from the parade after Quarry Pond. No family in this town is letting a child wear it tonight.",
    "parents": "The estate gates shut at ten. No real child is out past the third street without a parent standing somewhere behind them.",
    "bag": "A full bag rattles when it is shaken. If the bag makes no sound, it is not holding candy.",
    "bell": "St. Erth's rings eleven at eleven. Whatever arrives after the last note has died is not a child.",
}

# ----------------------------------------------------------------------- questions
QUESTIONS = {
    "costume": "🎭 Ask about the costume",
    "name": "🏷️ Ask their name",
    "school": "🏫 Ask which school they go to",
    "bag": "🎒 Ask what's in the bag",
    "parents": "👀 Ask if anyone is with them",
    "light": "💡 Ask them to step into the porch light",
    "smile": "😁 Ask them to smile at you",
    "breath": "❄️ Ask them to say trick or treat",
    "sweet": "🍬 Ask their favourite sweet",
    "why": "🏠 Ask why they chose your house",
    "time": "🕚 Ask what time it is",
}

# ------------------------------------------------------------------------ the cast
# breaks: {rule: where the tell lives} — "desc" or the id of a question they answer.
VISITORS: dict[str, dict[str, Any]] = {
    # ------------------------------------------------------------------ NIGHT 1
    "n1_trex": {
        "name": "Toby",
        "costume": "🦖 a cardboard T-Rex",
        "real": True,
        "breaks": {},
        "description": (
            "A boy of about seven stuffed into a cardboard T-Rex the size of a wardrobe. One eye of "
            "the head is taped shut, so he steers by memory and has come sideways down three houses "
            "of steps to get here. The porch light puts his shadow flat on the drive: small, boxy, "
            "ridiculous, attached."
        ),
        "answers": {
            "name": "*\"Toby.\"* He says it into the T-Rex's left knee, because the head is looking the wrong way.",
            "costume": (
                "*\"My dad made it. The arms don't move yet.\"* He demonstrates by sweeping your "
                "welcome mat off the step with one cardboard foot. *\"Sorry. They're still drying.\"*"
            ),
            "school": "*\"St. Erth's, year two.\"* The school on the parish sign, three streets back. He knows it.",
            "bag": "A pillowcase printed with pumpkins. It clinks with the sound of other people's sweets.",
            "sweet": "*\"Rockets. The red ones.\"* A pause. *\"Chocolate's fine too. I'm not fussy.\"*",
            "parents": "*\"Mum's at the end of the path. She's making everybody do the steps properly.\"*",
            "light": "He steps into the light before you finish asking, because he always does. The shadow comes with him.",
        },
        "give": (
            "*\"YES.\"* The T-Rex attempts a bow and loses an arm. He catches it against his hip with his "
            "good eye and is already backing away: *\"Thanks mister — happy Halloween — don't open for the "
            "tall ones—\"* and then he is gone, arm and all."
        ),
        "deny": (
            "He takes it the way a seven-year-old takes bad news. He says *\"that's fine\"* in a voice that "
            "is not fine, turns the T-Rex around with enormous effort, and goes sideways back down the path. "
            "At the gate he looks for somebody standing there. Somebody is."
        ),
        "truth": "Toby in the cardboard T-Rex was real, and he came with a warning nobody told him to give you.",
    },
    "n1_fairy": {
        "name": "Priya",
        "costume": "🧚 a fairy with glow-stick wings",
        "real": True,
        "breaks": {},
        "description": (
            "A girl in a green dress with plastic wings strapped over her coat, because her mother "
            "won. She has a torch in one hand and a bucket in the other and she is using both to see "
            "the step. Her breath fogs in front of her as she says good evening."
        ),
        "answers": {
            "name": "*\"Priya. And before you ask, yes, I'm too old for this, it's my little brother's year.\"*",
            "costume": (
                "*\"Wings were ninety pence at the shop. My mum put a coat under the dress, so I'm "
                "basically two people.\"* The glow sticks are green and one has gone pink and dying."
            ),
            "school": "*\"Fairview, years six to eleven.\"* Heavier tread than yours. She hums the bus route.",
            "bag": "*\"Two Maltesers, one plain, one butterscotch somebody's mum thought was a sweet coin.\"*",
            "sweet": "*\"Lynes. If you've got Lynes I will actually sing for you.\"*",
            "parents": "*\"My brother's at the gate. He's six and he's in the dinosaur. My mum's watching him.\"*",
            "breath": "She says it twice, and she means it. Her mouth fogs the air both times, wet and ordinary.",
        },
        "give": (
            "She picks out two, leaves one, and takes three. *\"For my brother,\"* she says, holding up "
            "one. Then, because she has been doing this an hour and has learned the street by heart: "
            "*\"You've got a tall one coming. Don't.\"*"
        ),
        "deny": (
            "She doesn't argue. She puts her torch back on your step rather than her face, says *\"he'll "
            "be gutted, actually\"* about her brother, and walks back down the path counting houses under "
            "her breath."
        ),
        "truth": "Priya with the glow-stick wings was real, and was trying to make the night fair for somebody smaller.",
    },
    "n1_smile": {
        "name": "Cassius",
        "costume": "🧛 a vampire cape, buttoned to the throat",
        "real": False,
        "breaks": {"teeth": "smile"},
        "scare": "behind_you",
        "description": (
            "A tall boy in a vampire cape, very straight posture, hands folded like somebody waiting "
            "for a bus. He carries a plastic jack-o'-lantern bucket. It is empty and dry, although it "
            "rained on this road four houses back and every other bucket on the street is wet."
        ),
        "answers": {
            "name": "*\"Cassius.\"* He says it the way somebody repeats a name they were handed five minutes ago.",
            "costume": (
                "*\"I made it myself.\"* The cape is new. There is no torn elastic, no felt pen on the hem, "
                "no name in the label, no mother's stitching at the shoulder where it pulled."
            ),
            "school": "*\"The school on the hill.\"* St. Erth's is on flat ground. The only hill is the reservoir.",
            "smile": (
                "He smiles when you ask, and then keeps smiling while you decide whether to say stop. "
                "The mouth has more teeth than a face holds, and every one of them is the same size."
            ),
            "sweet": "*\"Everybody gives me the same thing. Whatever you have will be fine.\"*",
            "why": "*\"Your light was on.\"* It is. It has been on all evening, and he is the only one who has come for it.",
        },
        "give": (
            "*\"Thank you.\"* He does not eat any of it. He sets the bowl down with the spoon still inside "
            "it, walks off the path without using the gate, and the porch light is the colour of pond water "
            "for the rest of the night."
        ),
        "deny": (
            "*\"All right,\"* he says, pleasantly. He does not move for a long moment after that. Then he "
            "turns — exactly, the way somebody turns when they have decided where they are going — and the "
            "step is cold where his feet were."
        ),
        "truth": "The polite vampire had too many teeth, and the same smile before and after he used it.",
    },
    # ------------------------------------------------------------------ NIGHT 2
    "n2_witch": {
        "name": "Dana",
        "costume": "🧹 a witch on a borrowed broom",
        "real": True,
        "breaks": {},
        "description": (
            "A girl of eleven in a hat three sizes too big, riding a garden broom she has clearly "
            "been told not to fly. She is impatient, she is cold, and her breath comes out of her "
            "in two grey clouds while she waits for you to decide."
        ),
        "answers": {
            "name": "*\"Dana. Dana Whitmore. My brother's Sam and he's a better-looking witch.\"*",
            "costume": (
                "*\"Hat's from the box in the loft, broom's from my nan's shed.\"* The hat has a biro name "
                "inside the band, in an adult's handwriting, three sizes down."
            ),
            "school": "*\"Fairview. Year seven. I've got a science project due and I'm at a door.\"*",
            "bag": "*\"It's a bin liner. Everyone at our house uses bin liners, it holds more.\"* It rattles like loot.",
            "sweet": "*\"Curly Wurly. If you give me a Boost I will be disappointed but I will not say anything.\"*",
            "parents": "*\"My nan's two doors down with the torch. She's not coming closer, she says I'm eleven.\"*",
            "breath": "She says *trick or treat* through her teeth on purpose to fog the air at you. *\"Satisfied?\"*",
        },
        "give": (
            "She takes the whole handful without slowing down, puts it in the bin liner, and hands the "
            "broom back to your porch rail because she cannot carry both. *\"Ta. Go to bed early, the "
            "tall ones are out.\"* She walks — properly walks, dragging the broom — to the next house."
        ),
        "deny": (
            "*\"Unbelievable.\"* She is too old to cry about it and too cold to make a speech, so she "
            "spins the broom around on the step and takes her disappointment two doors down, loudly, "
            "to somebody else."
        ),
        "truth": "Dana on the borrowed broom was real, and eleven, and owed her brother a better hat.",
    },
    "n2_robot": {
        "name": "Sam",
        "costume": "🤖 a cereal-box robot",
        "real": True,
        "breaks": {},
        "description": (
            "A small boy in a robot made of cereal boxes and foil, with a colander helmet he keeps "
            "pushing back off his eyes. He has not spoken yet. He is holding the box out at you with "
            "both hands like a present, and his breath steams inside the colander."
        ),
        "answers": {
            "name": "He lifts the colander. *\"Sam.\"* Then, because he has been told: *\"Sam Whitmore.\"*",
            "costume": (
                "*\"Me and my sister made it. She did the bits with the sellotape.\"* The boxes are "
                "taped at the seams and one side says BREAKFAST in half-erased marker."
            ),
            "school": "A long pause. *\"...Fairview.\"* Under the colander he is grinning at being caught out.",
            "bag": "The box is a biscuit tin with a hole cut in the lid. Inside: toffee, a plastic spider, a stone.",
            "sweet": "*\"The green ones. Not the ones with the fizz on top.\"*",
            "parents": "*\"Nan's down there with the torch. She says I have to say please.\"*",
            "light": "He stamps into the light to show off. The shadow of the colander comes with him and wobbles.",
        },
        "give": (
            "He says *\"thank you miss/sir\"* badly, at the wrong place in the sentence, and puts "
            "two pieces in the tin and immediately gives one back to you because he has more than "
            "he needs. Then he goes, colander sliding, without waiting for the door to close."
        ),
        "deny": (
            "He takes it without a word, which is worse. He pushes the colander back up, turns "
            "the little robot body around with both hands, and walks home to his sister with an "
            "empty biscuit tin and a stone in it."
        ),
        "truth": "Sam in the cereal-box robot was real, and had been coached about his manners, and meant them.",
    },
    "n2_still": {
        "name": "the snowman",
        "costume": "⛄ a snowman suit, three sizes too big",
        "real": False,
        "breaks": {"breath": "breath"},
        "scare": "ground_knock",
        "description": (
            "A child in a white snowman suit with cotton wool snowballs glued along the hump. The "
            "suit is far too big, so the shape of whoever is inside it keeps changing. It is four "
            "degrees, the road is wet, and the child is not shivering. Their bucket is on the step, "
            "not in their hand."
        ),
        "answers": {
            "name": "*\"Bo.\"* A second later, as if it has thought of a better one: *\"Bo Smith. Everybody calls me Bo.\"*",
            "costume": "*\"It's cold in it. I like the cold.\"* The cotton wool is dry, in a night that has soaked every other costume.",
            "school": "*\"The school. The one with the sign.\"*",
            "bag": "*\"Candy.\"* They do not shake it. They do not offer it. It is hanging from an empty hook on the suit.",
            "breath": (
                "*\"Trick or treat,\"* they say. The air in front of the mouth stays clear. It does "
                "not fog, or move, or fog, and the suit is too big for anything in it to be breathing."
            ),
            "why": "*\"You have the most lights.\"* Three bulbs. The street has better.",
        },
        "give": (
            "The sweets go into the suit at the shoulder and slide down inside it. They say *\"thank "
            "you, will you open the door\"* in the same voice they said trick or treat with, and the "
            "bottom of the costume lifts off the step and stays there, held up by nothing you can see."
        ),
        "deny": (
            "The head goes down. The suit stands at the bottom of the step a long time, and when it "
            "finally leaves it leaves the bucket behind, still hanging on its empty hook, and the "
            "cotton wool snowballs are warm when you throw them out."
        ),
        "truth": "The snowman did not breathe, and did not leave, until it had used up your whole porch light.",
    },
    # ------------------------------------------------------------------ NIGHT 3
    "n3_pirate": {
        "name": "Ellis",
        "costume": "🏴‍☠️ a pirate with an eyepatch over the wrong eye",
        "real": True,
        "breaks": {},
        "description": (
            "A kid in a striped jumper with a belt and a plastic cutlass, an eyepatch over the eye "
            "that was already good. They came down the path backwards once and blamed the cutlass. "
            "Their shadow does exactly what they do, a half-second late."
        ),
        "answers": {
            "name": "*\"Cap'n Ellis. With two L's, my nan says it's Spanish, I say it's pirate.\"*",
            "costume": "*\"It's my big uncle's belt. The patch's for the wound.\"* The patch is over the wrong eye and they will not move it.",
            "school": "*\"St. Erth's, year four, we've got the nativity practice and I'm a sheep.\"*",
            "bag": "A rucksack with the cutlass sticking out of it. It rattles with sweets and one very hard apple.",
            "sweet": "*\"Space Raiders. Any flavour. I don't choose, the ship chooses.\"*",
            "parents": "*\"Me dad's in the car at the top, engine on. He said six houses and then home.\"*",
            "light": "They salute the light and stand square in it. *\"Shadow's my first mate.\"* It is, and it follows.",
            "breath": "*\"ARH, TRICK OR TREAT.\"* A proper cloud of it, and they are pleased with themselves.",
        },
        "give": (
            "They put your sweets in the rucksack with the apple and the cutlass, and pay you in an "
            "orange broken into segments, which is worth more than the candy and they know it. *\"For "
            "the galley,\"* they say. Then, quieter, at the gate: *\"There's a girl outside in a wet "
            "dress. Don't be mean to her. She's not like the others.\"*"
        ),
        "deny": (
            "*\"That's alright, I've got the whole street.\"* They swing the cutlass at a hedge on the "
            "way out, miss, and don't look back at all, which takes effort. At the gate the car engine "
            "revs for them."
        ),
        "truth": "Cap'n Ellis was real, and told you about the wet dress, and you should remember who did.",
    },
    "n3_knight": {
        "name": "Noor",
        "costume": "🛡️ a knight with a dustbin-lid shield",
        "real": True,
        "breaks": {},
        "description": (
            "A tall girl in a grey duvet hood and a cardboard surcoat, carrying a plastic shield she "
            "holds like she has read about shielding. She knocks once on the rail with the shield, "
            "formally, and waits to be addressed."
        ),
        "answers": {
            "name": "*\"Noor. Dame Noor, actually, my little cousin knighted me with a butter knife.\"*",
            "costume": "*\"Duvet, pillowcase, and the lid off the recycling.\"* The shield still has a recycling sticker on the back.",
            "school": "*\"St. Erth's, year eight. I'm on leave from a chemistry revision session, which is worse than this.\"*",
            "bag": "*\"Tote bag. My mum's, she said not to say.\"* It is stuffed with other people's chocolate and one library book.",
            "sweet": "*\"Fudge. If you've got real fudge from the shop I'll pay you, honestly.\"*",
            "parents": "*\"Mum's at the end. She waved. She's waving.\"* A torch beam swings twice at the bottom of the path.",
            "light": "She steps in and holds the shield up so you can see behind her. The shadow is on the fence, complete, and salutes.",
            "time": "*\"Nearly eleven.\"* Her phone comes out at you, lit, showing the time and the battery and her wallpaper.",
        },
        "give": (
            "She accepts the candy with both hands and a small nod, like tribute, and puts exactly one "
            "in her mouth there on the step in defiance of every rule her mother has ever given her. "
            "*\"The next one's not a kid. I've seen it at four doors.\"*"
        ),
        "deny": (
            "*\"Understood,\"* she says, and means it, which is somehow humiliating. Shield first, "
            "backwards down the step, and she does not look at you again — she has a street to patrol."
        ),
        "truth": "Dame Noor was real, held the line at your rail, and had already clocked what was coming.",
    },
    "n3_wet": {
        "name": "the girl in the wet dress",
        "costume": "💧 a white dress, soaked through",
        "real": False,
        "harmless": True,
        "breaks": {"costume": "costume"},
        "description": (
            "A girl of about eight in a white dress with water running out of her hair onto the step "
            "in a steady line. She has no bucket. She holds her hands cupped in front of her, the way "
            "you hold something for somebody else. The costume is the drowned girl from Quarry Pond — "
            "the one the parade committee banned, and the one no family in this town would let a child "
            "put on tonight."
        ),
        "answers": {
            "costume": (
                "*\"This is what she wore. The girl in the pond.\"* She notices you noticing. *\"You're "
                "not allowed. I know. Everybody got told.\"*"
            ),
            "name": "*\"Nobody,\"* she says. *\"They stopped calling me that the day I went in.\"*",
            "bag": "*\"I don't have a bag. Nobody gave me one.\"* Her cupped hands have a thin shine on them.",
            "sweet": "*\"I don't eat. I only wanted to be allowed to hold something.\"*",
            "parents": (
                "*\"My mum comes for me at eleven. She always comes.\"* She looks at the road, and then "
                "at you, and then at the road again. *\"She's late tonight.\"*"
            ),
            "why": "*\"Because your light was on, and you were the only house that didn't close the curtains.\"*",
            "light": "She stands in the light. It goes through her and lands on the step behind her in a paler version of herself.",
        },
        "give": (
            "You put two sweets in her hands and she closes them very carefully, as if it is the first "
            "warm thing she has been given in eleven years. *\"Thank you,\"* she says. *\"She'll walk me "
            "home now. She's here.\"* The porch light steadies, and is only a light, and the step is dry "
            "where she stood, and always was."
        ),
        "deny": (
            "*\"Okay,\"* she says, and goes. At the gate she turns back once. *\"You did the right thing. "
            "You should be proud of it.\"* The line stays in your head for the remaining two nights, "
            "whatever else happens."
        ),
        "truth": "The girl in the wet dress was not a child. Nothing ever came of her, and she never came back.",
    },
    "n3_tall": {
        "name": "the tall dog",
        "costume": "🐕 a black dog costume, and very, very tall",
        "real": False,
        "breaks": {"shadow": "light"},
        "scare": "behind_you",
        "description": (
            "Someone in a black dog costume who is far too tall to be a child — the ears brush the "
            "hanging light. It has stayed at the bottom of the step, where the porch light does not "
            "reach, and it has not blinked since it arrived, which is not a thing children do."
        ),
        "answers": {
            "name": "*\"Biscuit.\"* It says this a beat too late, as though the answer was supplied to it.",
            "costume": "*\"This is me. This is the costume.\"* There is no zip, no seam, no mask edge at the neck.",
            "school": "*\"The one with the sign. The one with the sheep.\"*",
            "bag": "It has no bucket and does not seem to have noticed this omission.",
            "light": (
                "It comes up into the porch light and the boards under it stay unshaded. There is a "
                "dog shape, and there is nothing on the drive beside the dog shape."
            ),
            "why": "*\"It smelled like somebody was home.\"*",
            "parents": "*\"My owner's waiting.\"* It does not look at the gate when it says this.",
        },
        "give": (
            "It puts the candy in its mouth without using its hands and keeps looking at you while it "
            "does. Then it says *\"may I come in\"* with the same voice it used for *Biscuit*, and the "
            "hall light behind you goes out, and you hear the front door close by itself, gently, like "
            "it has been asked to."
        ),
        "deny": (
            "It sits down on the step. The step takes its weight like a step takes a weight. It watches "
            "the next three houses from your garden path, and the family at number nine finds a dog "
            "shape on their drive in the morning with no owner and no shadow."
        ),
        "truth": "The dog was a person's height and nobody's child, and it stayed in your garden until it was invited somewhere.",
    },
    # ------------------------------------------------------------------ NIGHT 4
    "n4_hellcat": {
        "name": "Roxy",
        "costume": "🐈‍⬛ a black cat with whiskers drawn on in eyeliner",
        "real": True,
        "breaks": {},
        "description": (
            "A girl of about nine in a school jersey with cat ears pinned to it, eyeliner whiskers "
            "already smudging down one cheek from the damp. She has been out an hour and is being "
            "brave about it. Her breath fogs the second time she opens her mouth."
        ),
        "answers": {
            "name": "*\"Roxy. It's not my real name, it's tonight's name.\"*",
            "costume": "*\"I did the whiskers myself. Look, they match.\"* They do not match. One is three centimetres longer.",
            "school": "*\"Fairview, year five. We've got sports day Thursday, I'm in the sack race.\"*",
            "bag": "*\"Three Haribo, two Marses, a thing that I think was a coin.\"* It rattles like a full tin.",
            "sweet": "*\"Strawbeds. The squishy ones. My gran buys them for me.\"*",
            "parents": "*\"My gran's at the corner with the dog. She can't walk up the steps anymore, that's why I'm by meself.\"*",
            "light": "She turns sideways in the light to show you the whole shadow, tail and all. *\"See? Cat.\"*",
            "time": "*\"Ten-thirty. Gran said eleven sharp and I've got four houses to go.\"*",
        },
        "give": (
            "She counts them into the bag out loud, wrong, and doesn't care. *\"Ta. Are you the one who "
            "was mean to the little ones? That's what the boy at nine said.\"* She takes your judgement "
            "about as seriously as a nine-year-old can, and goes to tell somebody."
        ),
        "deny": (
            "Her face does the thing children's faces do when they are trying not to be cruel back. "
            "*\"It's fine. Gran's waiting. I'm not gonna tell her, if that's what you're worried about.\"* "
            "The eyeliner is running and she pretends it is the rain."
        ),
        "truth": "Roxy with the drawn-on whiskers was real, and her gran was at the corner, and she remembered your name.",
    },
    "n4_vampire2": {
        "name": "Callum",
        "costume": "🧛 a second vampire, with a plastic fang",
        "real": True,
        "breaks": {},
        "description": (
            "A boy of about nine in a shop cape, one fang stuck on crooked, holding a torch under his "
            "own chin to frighten you and getting most of the light in his own eyes instead. He has a "
            "name sticker on the cape, and somebody's handwriting on it. His shadow has the fang on it."
        ),
        "answers": {
            "name": "*\"Count Callum.\"* He lifts the torch. Under it he is a kid with a smudge of chocolate on his chin.",
            "costume": "*\"It's from the shop, it was four pounds. My mum's got the receipt.\"* The name tag inside says CALLUM M, size 5.",
            "smile": "He grins at you, deliberately hideous, and the plastic fang falls off into his hand. *\"I'll get my mum to fix it.\"*",
            "school": "*\"St. Erth's. Year three. I'm in the choir but I'm not doing the solfa again.\"*",
            "bag": "*\"Two Smarties, a raisin, somebody gave me a raisin.\"* He is furious about the raisin.",
            "sweet": "*\"Dairly Milk. The big one. I'll trade you the raisin for it.\"*",
            "parents": "*\"Dad's at the gate pretending he isn't. He's been pretending all night.\"*",
            "light": "He shuffles into the light and points his own shadow out to you, pleased, fang and all.",
            "breath": "*\"Trick or treat,\"* he says, and fogs, and laughs at his own fog, and tries it again.",
        },
        "give": (
            "*\"MUM. HE GAVE ME A BIG ONE.\"* He shows the bar to the gate, to a man who very clearly "
            "was not pretending, and then he is back up the path for one more: *\"have you got any more "
            "raisins, I've got a raisin for you.\"*"
        ),
        "deny": (
            "*\"DAD. HE'S NOT GIVING ME ANY.\"* The man at the gate comes up the path, apologises for "
            "the hour, takes Callum by the shoulder, and they go back down the road together, arguing "
            "about raisins."
        ),
        "truth": "The second vampire was real, four pounds, shop-bought, and had a father at the gate the entire time.",
    },
    "n4_invited": {
        "name": "the girl with no bag",
        "costume": "👻 a bedsheet with two holes cut badly",
        "real": False,
        "breaks": {"door": "why"},
        "scare": "window_flash",
        "description": (
            "A small shape under a bedsheet with two eye holes cut badly and unevenly, one over nothing "
            "at all. It has no bucket, no bag, no pillowcase. It has both hands flat against the door "
            "already, before you opened it, and there is somebody else standing behind it at the edge "
            "of the path, further back than the light goes."
        ),
        "answers": {
            "name": "*\"I'm a ghost,\"* it says, from inside the sheet, and the top of the sheet does not move when it talks.",
            "costume": "*\"It's my sheet. I cut it. I cut it meself.\"* The holes are cut from the wrong side, and one is over the ear.",
            "sweet": "*\"We don't want sweets. We want to be in out of it. It's so cold out here.\"*",
            "parents": "*\"My friend's behind me. She's waiting for you to say it.\"*",
            "why": "*\"I don't want candy,\"* she says. *\"I want you to open the door proper. She can't get in unless you invite her.\"*",
            "bag": "*\"It's empty. That's why we need the bowl. Put the bowl on the step and I'll fill it.\"*",
        },
        "give": (
            "The candy goes onto the step, not into the sheet. *\"Ta. Now the bowl.\"* You have already "
            "given away what you had, and the sheet crouches over the sweets on your paving with both "
            "hands flat on the boards, and the thing at the edge of the path comes to the gate, and "
            "stops there, because it has not been invited yet and it knows you can see it."
        ),
        "deny": (
            "*\"You wouldn't even let us warm up?\"* The sheet does not move for a while, and then both "
            "shapes walk off together, small one first, and the gate closes behind them without a sound. "
            "Your hall light has been off the whole time they were talking."
        ),
        "truth": "The sheet had no bag because it did not want candy, and the second shape never came past the gate you shut.",
    },
    "n4_gates": {
        "name": "the astronaut",
        "costume": "👨‍🚀 a spacesuit with a scratched helmet",
        "real": False,
        "breaks": {"parents": "parents"},
        "scare": "wrist",
        "description": (
            "A child in a silver spacesuit with a fishbowl helmet, scratched so badly that you cannot "
            "see the face inside it at all. They came from up the road, past the third street, and "
            "there is nobody at the gate behind them and no torch anywhere on the lane."
        ),
        "answers": {
            "name": "A muffled voice through the scratches: *\"Commander.\"*",
            "costume": "*\"It's mine. It's from America.\"* The suit is a size too large and the gloves are on the wrong hands.",
            "school": "*\"I'm home-schooled. I'm from very far away. Past the third street.\"*",
            "parents": (
                "*\"Nobody's with me. The gates were open.\"* The estate gates shut at ten and it is "
                "a quarter past eleven, and nothing behind them on the road is standing anywhere."
            ),
            "bag": "A silver sack. It does not clink when they turn it over for you; it moves like something is shifting inside it.",
            "why": "*\"Your light's the one that's nearest the gate. I came through it.\"*",
            "light": "The helmet takes the porch light and scatters it, so there is a shadow and it is a helmet-shaped one and there is nothing at all inside the visor.",
        },
        "give": (
            "The sack goes down on the step and the candy goes into it and something in it answers. "
            "They wave with the wrong hand and walk back up the road past the third street without "
            "once turning round, and the estate gate is shut behind them and was shut before them."
        ),
        "deny": (
            "*\"That's alright. I've got the whole estate.\"* They tap your door frame twice from the "
            "outside, in a pattern that is not knocking, and go. In the morning the scratches on the "
            "inside of your own hall mirror are on the inside."
        ),
        "truth": "The astronaut came through the wrong gate alone at a quarter past eleven, and the visor had nothing behind it.",
    },
    # ------------------------------------------------------------------ NIGHT 5
    "n5_mummy": {
        "name": "Theo",
        "costume": "🧻 a mummy made of toilet roll",
        "real": True,
        "breaks": {},
        "description": (
            "A boy wrapped in toilet paper, badly, with one eye free and a gap at the ribs where he "
            "ran out. It has started unspooling behind him down the path. He is shivering and proud "
            "and every breath steams, and a woman two houses back is laughing at him through a torch."
        ),
        "answers": {
            "name": "*\"Theo. I've got two layers left so don't ask me to bend.\"*",
            "costume": "*\"Forty-one rolls. My dad counted. I'm up to my knees and it's only to here.\"*",
            "smile": "He grins, and it is the most ordinary grin in the world: gaps, one tooth going, chocolate in the middle.",
            "school": "*\"Fairview. Year six. I'm supposed to be revising.\"*",
            "bag": "There is no bag; there is a pillowcase under the bandages at the ribs, which he claims is structural.",
            "sweet": "*\"Anything with a wafer in it. I'll take the ones I hate too, I'm not proud.\"*",
            "parents": "*\"That's me dad with the torch two doors up. He's the one who wrapped me.\"*",
            "light": "He turns, slowly, the whole roll. His shadow is a mummy and it drags a long tail of it up the path.",
            "breath": "*\"Trick or treat,\"* he says with his mouth open on purpose, and the fog comes out of the bandages.",
        },
        "give": (
            "*\"DAD. HE DID IT. THE MUMMY GOT ONE.\"* His father does not come up the path but he does "
            "raise the torch twice, which on this street is applause. Theo shuffles off backwards, "
            "leaving a metre of toilet paper on your step for the wind to deal with."
        ),
        "deny": (
            "*\"Fair enough, I'm a bit wet.\"* He is generous about it, which is worse than an argument. "
            "He shuffles off to number eleven and the man with the torch waits for him at the gate even "
            "though it is his own house two doors up."
        ),
        "truth": "Theo the mummy was real, forty-one rolls, and every bit of him breathed.",
    },
    "n5_skeleton": {
        "name": "Iris",
        "costume": "💀 a skeleton onesie, with a torch clipped to it",
        "real": True,
        "breaks": {},
        "description": (
            "A girl in a black skeleton onesie with a clip-on torch on the chest that she has left on "
            "all night to read her phone by. She is the last one out and she knows it. She has done "
            "this street twice and has a list. Her shadow is thin and correct and holds a phone."
        ),
        "answers": {
            "name": "*\"Iris. I'm being efficient, I'm Iris.\"*",
            "costume": "*\"Bought it, I'm not stupid, it's minus three degrees.\"* The zip works and there is a label in the neck.",
            "smile": "She smiles without being asked, briefly, to be helpful: ordinary teeth, an orthodontic thing on one side.",
            "school": "*\"St. Erth's, year nine. I've got a coursework deadline on Tuesday so I'm on a schedule.\"*",
            "bag": "*\"Two hundred and forty grams by weight, I'm not guessing.\"* She shakes it and it answers her.",
            "sweet": "*\"Peaceful chocolate. I know that's a children's one.\"*",
            "parents": "*\"My sister's at the top of the lane with the car. She's sixteen and it's mortifying.\"*",
            "time": "*\"Eleven o'clock, and the bell's just finished, so I've cut it fine and I know.\"* Fog, breath, phone, torch.",
            "why": "*\"Because you're the last one on my list with the light on, and I'd like to finish.\"*",
        },
        "give": (
            "She puts your candy in and reads the weight off her phone screen, then looks up. *\"Oh, "
            "thank you, that's actually the last one, I was going to have to knock on the shutters at "
            "eleven.\"* She gives you her orange segment in exchange, because somebody taught her, and "
            "the car at the top of the lane beeps for her."
        ),
        "deny": (
            "*\"Ah.\"* No argument at all. She ticks something on her phone, says *\"you've got a good "
            "lock, mind,\"* which is not what you said, and walks back up the lane to the last house "
            "with the shutters still closed at eleven o'clock."
        ),
        "truth": "Iris in the skeleton onesie was real, and she was eleven minutes from finishing a job she had planned.",
    },
    "n5_silent": {
        "name": "the boy with the hard bucket",
        "costume": "🎃 an orange plastic pumpkin bucket",
        "real": False,
        "breaks": {"bag": "bag"},
        "scare": "chalk",
        "description": (
            "A child in a hoodie and a rubber bat mask, holding a hard plastic pumpkin bucket low "
            "and level, the way you hold something you don't want to be asked to show. Everything "
            "about them is ordinary. It is the eleventh hour, the lane is empty, and their breathing "
            "fogs, and their shadow is there."
        ),
        "answers": {
            "name": "*\"Kai.\"* Short. He wants this over with.",
            "costume": "*\"My brother's. He's at home.\"* The mask has been cut with scissors at the eye holes, and badly.",
            "school": "*\"St. Erth's. Year seven.\"*",
            "bag": (
                "He tips the bucket for you and it makes no sound. Nothing slides, nothing rattles, "
                "and a bucket with sweets in it is the loudest thing on any child's arm."
            ),
            "sweet": "*\"Whatever. Chocolate.\"*",
            "parents": "*\"Down the lane. He's slow.\"*",
            "light": "He stands in it properly, and his shadow comes with him, and he is annoyed that you made him.",
            "breath": "He breathes. He fogs. He has thought about this, and everything except the bucket is correct.",
        },
        "give": (
            "The bucket takes the candy without a sound, and the sound it makes when he sets it down "
            "on your step is not a sound sweets make. *\"Ta,\"* he says, and the mask does not go with "
            "his head when he turns it."
        ),
        "deny": (
            "*\"Have it then.\"* He takes the bucket with both hands now, level, and walks up the lane "
            "carefully, the way you carry something that must not be disturbed. There is nobody behind "
            "him, and at the top he turns the wrong way and is not there anymore."
        ),
        "truth": "The boy was warm, and shadowed, and correct, and his bucket was silent all night.",
    },
    "n5_bell": {
        "name": "the one after the bell",
        "costume": "🕯️ a candlelit paper lantern held wrong",
        "real": False,
        "breaks": {"bell": "time", "shadow": "desc"},
        "scare": "bell",
        "description": (
            "It comes up the path after the bell has finished ringing, which is the first thing wrong "
            "with it, and it holds a paper candle lantern by the flame rather than the handle. Its "
            "feet come into the porch light and leave the light unbroken, with nothing lying on the "
            "drive behind them."
        ),
        "answers": {
            "name": "*\"You know me,\"* it says, and you do not, and it is not unkind about that.",
            "costume": "*\"Lantern for the pond. They do it at eleven.\"* Your own kitchen clock says twenty past.",
            "time": (
                "*\"Ten o'clock,\"* it says, and behind the church the bell is still swinging toward the "
                "eleventh note, and it rang eleven a full minute before this thing reached your step."
            ),
            "sweet": "*\"Leave it out. You don't have to give me much.\"*",
            "why": "*\"You're the last one with the curtains open. You're always the last one.\"*",
            "breath": "*\"Trick or treat,\"* it says, and the air is fogged. It has learned that one from somewhere.",
            "light": "It waits in the light while you look at the drive. There is a figure and no length of it, no shadow at all on the paving.",
        },
        "give": (
            "It puts the lantern down and takes the candy into a hand that has too many joints, and "
            "says your name — the one the town uses, the one you set — in a voice that has been "
            "practising it. *\"We'll walk up together,\"* it says. It is still walking up. It is always "
            "going to be walking up."
        ),
        "deny": (
            "*\"Fair,\"* it says, and it is fair about it, and it goes. The bell rings eleven again at "
            "eleven, which it did not do, and there is a paper lantern sitting on your step with the "
            "candle still warm, lit at twenty past eleven for somebody who is not here to see it."
        ),
        "truth": "It came after the last note, carried its own light by the flame, and never once threw a shadow.",
    },
}

# ------------------------------------------------------------------------ nights
NIGHTS = [
    {
        "night": 1,
        "brief": (
            "The first night the street is still a street. Torches at gates, parents in cars, the "
            "smell of burnt toffee from number nine. The note under your door is the one every house "
            "on this lane gets, and you have hung it on the hook since you moved in."
        ),
        "rules": ["shadow", "teeth", "door"],
        "visitors": ["n1_trex", "n1_fairy", "n1_smile"],
    },
    {
        "night": 2,
        "brief": (
            "The cold comes in off the reservoir at half past nine and nobody goes home. Two more "
            "houses on the lane put their lights out early tonight and did not say anything about it "
            "in the morning."
        ),
        "rules": ["shadow", "teeth", "door", "breath"],
        "visitors": ["n2_witch", "n2_robot", "n2_still"],
    },
    {
        "night": 3,
        "brief": (
            "Half the street has started writing names on the back of the rule note, in pencil, "
            "crossing them out later. Somebody has taped a printed photograph of the drowned girl "
            "to the parade noticeboard, and taken it back off again."
        ),
        "rules": ["shadow", "teeth", "door", "breath", "costume"],
        "visitors": ["n3_pirate", "n3_knight", "n3_wet", "n3_tall"],
    },
    {
        "night": 4,
        "brief": (
            "The estate gate was found open at ten-forty and shut again, and nobody admits to it. Two "
            "families have put the bowl on the step and stopped opening the door at all. You are still "
            "opening it."
        ),
        "rules": ["shadow", "teeth", "door", "breath", "costume", "parents"],
        "visitors": ["n4_hellcat", "n4_vampire2", "n4_invited", "n4_gates"],
    },
    {
        "night": 5,
        "brief": (
            "The last night. St. Erth's rings eleven, and after that the lane belongs to whatever is "
            "still walking it. Every house on the road has its light on. That is not a coincidence and "
            "that is not a comfort."
        ),
        "rules": ["shadow", "teeth", "door", "breath", "costume", "parents", "bag", "bell"],
        "visitors": ["n5_mummy", "n5_skeleton", "n5_silent", "n5_bell"],
    },
]

# ----------------------------------------------------------------------- supplies
# Marla keeps The Last Customer, which is on this lane and never seems to close.
SUPPLY = {
    "npc": "☕ Marla, from The Last Customer",
    "warm": (
        "Marla leaves a box on your step, still warm from the counter, with a rubber band round the "
        "lid. *\"You've been decent,\"* she says through the door. *\"Word gets along this lane. Take "
        "what you need and don't be generous to things that thank you twice.\"*"
    ),
    "terse": (
        "A box on the step, lid not quite shut, no knock. Marla is three houses down with her back to "
        "you, talking to somebody you cannot see. She holds up two fingers without turning round: two "
        "caramels, and no conversation about it."
    ),
    "cold": (
        "The box is on the step and somebody has written on it in felt pen: *FOR THE HOUSE THAT "
        "REFUSED*. Marla does not come out of the diner when you take it in. The till light stays on "
        "until three in the morning, and the door is locked from the inside."
    ),
    "wet_fed": (
        "Marla stops on the step with the box still in her hand. *\"You gave her something.\"* It is not "
        "a question. *\"Nobody's done that. Whatever she was to you — you'll not have it back, and she'll "
        "not have it either. Keep the light on.\"*"
    ),
    "wet_denied": (
        "*\"She came to you,\"* Marla says, not unkindly, and looks at the gate. *\"You were right and "
        "you'll think about that till February. I did the same thing in '94 and I still check the "
        "curtains.\"*"
    ),
}

ENDINGS = {
    "bad": {
        "title": "🕯️ THE DOOR WAS OPEN",
        "text": (
            "Something you handed sweets to is inside, and it did not come in through the door — that "
            "was the part the note was warning you about. The porch light stays on. It never goes off "
            "again, and the street learns quickly that nobody answers your gate now, not even you.\n\n"
            "The families on this lane put your name on the back of their own rule notes, in pencil, "
            "and cross it out."
        ),
    },
    "happy": {
        "title": "🍬 FIVE NIGHTS, AND THE STREET IS STILL A STREET",
        "bands": {
            "warm": (
                "Five nights, and every child that came to your light went home with something, and "
                "nothing came in.\n\nIn the morning there is a bag on your step from somebody who did "
                "not knock: three toffees and the orange segment you were given on the third night, "
                "returned. The note goes back on the hook. Next October you will be at the gate with a "
                "torch, watching somebody else's children do the steps properly."
            ),
            "middle": (
                "Five nights, and the house still stands, and the light still works.\n\nThe street "
                "nods to you and does not say more than that. You sent away what needed sending, and "
                "there were two or three you could not be sure about, and being sure was never in it. "
                "You keep the note on the hook and you leave the bowl half full."
            ),
            "cold": (
                "Five nights, and you survived all of them.\n\nThe lane knows what you refused. There "
                "is a child at number eleven who tells her brother your street is the one to miss, and "
                "the parents have started leaving their boxes on your step rather than knocking, "
                "because a locked door is easier to plan around. Nothing came in. Nobody thanks you for it."
            ),
        },
    },
    "secret": {
        "title": "💧 THE ONE WHO WENT HOME DRY",
        "text": (
            "Five nights, and you never once let anything past the step — except the one the rules "
            "said you should not, and she never came back for you.\n\nIn the morning the gate is wet "
            "and there are two toffees sitting on the top rail, squared up, in the order you gave them "
            "to her. Marla says the pond has been odd all winter: it freezes at the edge first, in a "
            "ring, and the middle never takes.\n\nYou were never afraid again on a night like that one. "
            "Whatever watched your door from the third street on was not it, and there is a shape in "
            "the hall mirror at eleven o'clock that stands slightly further back than it should, and "
            "does not come closer. You gave her something to hold. She gave you the rest of the street.\n\n"
            "**The rules said no. You did anyway, and it was the only correct thing you did all week.**"
        ),
    },
}

# ------------------------------------------------------------------- consequences
def visitor(night: int, slot: int) -> dict[str, Any]:
    """The visitor at a night/slot position, with the id the log rows and the UI both need."""
    key = NIGHTS[night - 1]["visitors"][slot]
    return {**VISITORS[key], "id": key}


def is_harmless(v: dict[str, Any]) -> bool:
    """Anomaly that asks for nothing and takes nothing but a sweet."""
    return bool(v.get("harmless"))


def resolve(v: dict[str, Any], give: bool) -> dict[str, Any]:
    """Pure consequence of one decision, so the validator and the store agree."""
    outcome = {
        "hearts": 0,
        "reputation": 0,
        "candy": -1 if give else 0,
        "secret": False,
        "text": v["give"] if give else v["deny"],
        "scare": None,
        "correct": None,
    }
    if v["real"]:
        if give:
            outcome["reputation"] = REP_GIVE_REAL
            outcome["correct"] = True
        else:
            outcome["reputation"] = REP_DENY_REAL
            outcome["correct"] = False
        return outcome
    outcome["scare"] = v.get("scare") if give else None
    if is_harmless(v):
        outcome["secret"] = give
        outcome["correct"] = None
        return outcome
    if give:
        outcome["hearts"] = HEART_COST
        outcome["reputation"] = REP_GIVE_ANOMALY
        outcome["correct"] = False
    else:
        outcome["correct"] = True
    return outcome


def band(reputation: int) -> str:
    if reputation >= 80:
        return "warm"
    if reputation >= 40:
        return "middle"
    return "cold"


def supply_band(reputation: int) -> str:
    if reputation >= 80:
        return "warm"
    if reputation >= 40:
        return "terse"
    return "cold"


def happy_text(reputation: int) -> str:
    return ENDINGS["happy"]["bands"][band(reputation)]


def candy_budget() -> int:
    """Total candies a run can ever hold: the start plus every delivery."""
    return START_CANDY + SUPPLY_PER_NIGHT * (NIGHTS_TOTAL - 1)


def real_count() -> int:
    return sum(1 for v in VISITORS.values() if v["real"])


# ---------------------------------------------------------------------- validator
ANSWER_LIMIT = 320
DESC_LIMIT = 900
REACT_LIMIT = 700
BRIEF_LIMIT = 500


def _ids_in_nights() -> list[str]:
    out: list[str] = []
    for plan in NIGHTS:
        out.extend(plan["visitors"])
    return out


def validate_door() -> tuple[list[str], list[str]]:
    """Structure and fairness. A night that cannot be deduced is a broken night."""
    errors: list[str] = []
    warnings: list[str] = []

    listed = set(VISITORS)
    used = _ids_in_nights()
    for vid in used:
        if vid not in listed:
            errors.append(f"candy: night plan references unknown visitor '{vid}'")
    for vid in sorted(listed - set(used)):
        errors.append(f"candy: {vid} is written but never arrives at any door")
    if len(used) != len(set(used)):
        errors.append("candy: a visitor is scheduled twice; each door opens once per run")

    night_of = {vid: plan["night"] for plan in NIGHTS for vid in plan["visitors"]}
    active = {plan["night"]: set(plan["rules"]) for plan in NIGHTS}

    if len(NIGHTS) != NIGHTS_TOTAL:
        errors.append(f"candy: NIGHTS_TOTAL is {NIGHTS_TOTAL} but there are {len(NIGHTS)} nights")
    for plan in NIGHTS:
        night = plan["night"]
        if len(plan["visitors"]) < 3:
            errors.append(f"candy: night {night} has fewer than three visitors")
        if len(plan["visitors"]) > 4:
            errors.append(f"candy: night {night} has more than four visitors; the night summary embed will not fit")
        if not plan["rules"]:
            errors.append(f"candy: night {night} has no rule card, so nothing can be judged")
        for rule in plan["rules"]:
            if rule not in RULES:
                errors.append(f"candy: night {night} cites an unknown rule '{rule}'")
        if len(str(plan["brief"])) > BRIEF_LIMIT:
            errors.append(f"candy: night {night} brief is too long to print on the card")
        if not any(not VISITORS[v]["real"] for v in plan["visitors"] if v in VISITORS):
            errors.append(f"candy: night {night} has no anomaly; nothing to catch")
        if not any(VISITORS[v]["real"] for v in plan["visitors"] if v in VISITORS):
            errors.append(f"candy: night {night} has no real child; the reputation mechanic has nothing to do")

    # The card is cumulative: a rule printed on night 2 was printed on night 1 too,
    # otherwise a player who learned the tell earlier meets it again undocumented.
    seen: set[str] = set()
    for plan in NIGHTS:
        fresh = set(plan["rules"]) - seen
        if plan["night"] > 1 and not set(plan["rules"]) >= seen:
            errors.append(f"candy: night {plan['night']} drops rules the player was already given")
        if plan["night"] > 1 and len(fresh) > 2:
            warnings.append(
                f"candy: night {plan['night']} introduces {len(fresh)} new rules at once; that is a lot to read at a door"
            )
        seen |= set(plan["rules"])

    harmless = [vid for vid, v in VISITORS.items() if v.get("harmless")]
    if len(harmless) != 1:
        errors.append(f"candy: expected exactly one harmless anomaly for the secret ending, found {len(harmless)}")
    for vid in harmless:
        if VISITORS[vid]["real"]:
            errors.append(f"candy: {vid} is flagged harmless but is a real child; the secret must cost the player something")

    if candy_budget() < real_count():
        errors.append(
            f"candy: a run can hold {candy_budget()} sweets but {real_count()} real children arrive — "
            "a careful player could not feed them all"
        )
    if candy_budget() > real_count() + 3:
        warnings.append(
            f"candy: {candy_budget()} sweets available against {real_count()} real children; "
            "the bowl is never tight enough to force a decision"
        )

    for vid, v in VISITORS.items():
        night = night_of.get(vid, 1)
        for field in ("name", "costume", "description", "give", "deny", "truth"):
            if not str(v.get(field, "")).strip():
                errors.append(f"candy: {vid} has no {field}")
        if len(str(v.get("description", ""))) > DESC_LIMIT:
            errors.append(f"candy: {vid} description is too long for the door embed")
        for field in ("give", "deny", "truth"):
            if len(str(v.get(field, ""))) > REACT_LIMIT:
                errors.append(f"candy: {vid} {field} is too long")
        if not isinstance(v.get("real"), bool):
            errors.append(f"candy: {vid} must state whether it is real")
        answers = v.get("answers") or {}
        if len(answers) < 4:
            errors.append(f"candy: {vid} answers fewer than four questions; the select menu is empty")
        for qid, text in answers.items():
            if qid not in QUESTIONS:
                errors.append(f"candy: {vid} answers '{qid}', which nobody can ask")
            if not str(text).strip():
                errors.append(f"candy: {vid}/{qid} has an empty answer")
            if len(str(text)) > ANSWER_LIMIT:
                errors.append(f"candy: {vid}/{qid} answer is too long for one embed line")
        breaks = v.get("breaks") or {}
        if v["real"]:
            if breaks:
                errors.append(f"candy: {vid} is a real child but breaks {sorted(breaks)}; it cannot be judged fairly")
            continue
        if not breaks:
            errors.append(f"candy: {vid} is an anomaly that breaks no stated rule; the player cannot deduce it")
        for rule, tell in breaks.items():
            if rule not in RULES:
                errors.append(f"candy: {vid} breaks unknown rule '{rule}'")
            elif rule not in active.get(night, set()):
                errors.append(
                    f"candy: {vid} breaks '{rule}' but night {night}'s card does not print it, so the break is invisible"
                )
            if tell != "desc" and tell not in answers:
                errors.append(f"candy: {vid} tells '{rule}' with question '{tell}' but never answers it")
        scare = v.get("scare")
        if scare and scare not in story.SCARES:
            errors.append(f"candy: {vid} uses scare '{scare}', which the story does not define")

    for rule in RULES:
        if not any(rule in (v.get("breaks") or {}) for v in VISITORS.values()):
            warnings.append(f"candy: the rule '{rule}' is printed but nothing ever breaks it")
    for qid in QUESTIONS:
        if len(QUESTIONS[qid]) > 95:
            errors.append(f"candy: question '{qid}' label is too long for a select option")
        if not any(qid in (v.get("answers") or {}) for v in VISITORS.values()):
            warnings.append(f"candy: nobody can answer '{qid}'; it never appears in the menu")

    for key in ("bad", "happy", "secret"):
        if key not in ENDINGS:
            errors.append(f"candy: ending '{key}' is missing")
    if len(ENDINGS["happy"]["bands"]) != 3:
        errors.append("candy: the happy ending needs warm, middle and cold reputation bands")
    for field in ("warm", "terse", "cold", "wet_fed", "wet_denied"):
        if not str(SUPPLY.get(field, "")).strip():
            errors.append(f"candy: supply scene '{field}' is missing")

    return errors, warnings
