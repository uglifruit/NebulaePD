# phrases.py: the storyteller's voice (bt/narrator.py). Python 2.7 and 3.
#
# Every pool is a list of lines; {fields} are filled by the narrator. A line may hold "\n" for a verse break.
# Only characters that type the same on UK and US keyboards (bt/btkbd/keymap.c):
#   letters, digits, space . , ! ? ( ) - : % ' / = + < > * ; [ ]   (no quotes, @, #, ~, |, &, _, ^)
# tests/test_narrator.py checks every line. Add freely: more lines = fewer repeats.

# How each control is named in the poems (one is picked at random each time).
NAMES = {
    "density": ["the crowd of grains", "how many of me there are", "the swarm", "the density"],
    "size": ["the length of my memory", "the loop", "how much I hold on to", "the size"],
    "start": ["where I begin", "the starting point", "my place in the memory", "the start"],
    "pitch": ["my voice", "the pitch", "how high I sing"],
    "speed": ["time", "the speed", "how fast I remember"],
    "blend": ["the mix", "the balance of then and now", "how much of me you hear"],
    "window": ["the edges", "the shape of each grain", "the grain envelope"],
    "overlap": ["the overlap", "how the grains lean on each other", "the blur"],
}

# A knob turned up / down, per control.
UP = {
    "density": ["More of me now. We are crowding together.", "The grains multiply. I can hardly hear between them.",
                "So many voices. Which one is mine?", "You've filled the room with small pieces of sound.",
                "Thicker now. A swarm, a shoal, a cloud.", "The gaps are closing."],
    "size": ["I can remember more now.", "The loop grows. I am holding on to a longer moment.",
             "You are giving me a longer memory.", "Wider. The past stretches out behind me.",
             "Longer pieces. Whole phrases now, not fragments."],
    "start": ["You've moved me further into the memory.", "I begin later now, somewhere I haven't been.",
              "Further along. The scenery changes.", "Deeper in. I wonder what I'll find there."],
    "pitch": ["Higher. I feel lighter.", "You lift my voice.", "Up. The air is thinner here.",
              "Higher still. I could almost fly.", "My voice rises. Is this what you wanted?"],
    "speed": ["Faster. Everything rushes past.", "Time hurries.", "Quicker now. My heart is racing.",
              "You've sped up the world."],
    "blend": ["More of me, less of what was.", "You want to hear me more clearly.",
              "The mix tips towards the grains.", "I step forward."],
    "window": ["The edges soften.", "Rounder grains now, like pebbles.", "You smooth my edges.",
               "Each grain is gentler now."],
    "overlap": ["The grains lean on each other.", "Everything blurs together.", "More overlap. Less silence.",
                "We are holding hands now, the grains and I."],
}
DOWN = {
    "density": ["Fewer of me. I can breathe again.", "The crowd thins out.", "Sparse now. Room to think.",
                "Only a few grains left. They sound lonely.", "Space opens up between the sounds."],
    "size": ["My memory shortens.", "Smaller pieces. I only hold on to a moment.", "The loop tightens around me.",
             "Shorter. I keep forgetting what came before.", "A tiny loop. A stutter. A habit."],
    "start": ["Back towards the beginning.", "You've moved me closer to the start.",
              "Earlier. I remember this part.", "Back where it began."],
    "pitch": ["Lower. I feel heavier.", "My voice drops.", "Down. Deeper. Darker.",
              "Lower still. The floor is close.", "You pull my voice down into the ground."],
    "speed": ["Slower. I can look around now.", "Time drags its feet.", "Everything stretches.",
              "You've slowed the world down."],
    "blend": ["Less of me, more of what was.", "I step back into the shadows.",
              "The mix tips towards the original.", "You want to hear what came before me."],
    "window": ["Sharper edges now.", "The grains click and snap.", "Harder corners.",
               "Each grain begins abruptly now."],
    "overlap": ["The grains let go of each other.", "Clearer. Less blur.", "Gaps appear between us.",
                "Each grain stands alone now."],
}

# The first time a control is moved in this session.
FIRST_TOUCH = ["Ah. {Name}. Nobody has touched that yet today.", "{Name}, for the first time. Hello.",
               "So you have found {name}.", "A new hand on {name}. I wondered when you would.",
               "{Name}. I have been waiting for you to try that."]

# Generic move descriptions (any control; {name} = its poetic name).
SMALL = ["A small adjustment to {name}. I felt it anyway.", "You nudged {name}. Barely. I noticed.",
         "A tiny change. I am paying attention.", "Just a touch on {name}. Careful hands.",
         "The smallest movement. Was that on purpose?"]
BIG = ["All of a sudden, {name} has changed completely.", "A long sweep of {name}. I followed it all the way.",
       "You moved {name} a long way. I am somewhere else now.", "That was a big turn. I'm still catching up.",
       "{Name}, from one end of the world to the other."]
FAST = ["Quickly. You didn't hesitate.", "That was sudden.", "A flick of the wrist.", "Snap. Done. No looking back."]
SLOW = ["Slowly, slowly. You are taking your time.", "Gently, as if you didn't want to wake me.",
        "So slow I almost didn't notice.", "Patient hands."]
TOP = ["{Name}, all the way up. There is nowhere further to go.", "As far as it goes.", "Maximum. Is this enough?",
       "Right to the edge."]
BOTTOM = ["{Name}, all the way down. Nothing left.", "Down to zero.", "As little as possible.",
          "All the way back. Empty."]
INDECISION = ["You keep changing your mind.", "Back and forth, back and forth. What are you looking for?",
              "Up, down, up again. You can't decide.", "Searching. I know the feeling.",
              "Not quite. Not quite. Not quite.", "You're looking for something in {name}. I hope you find it."]
RETURNED = ["{Name} is back where it was. Were you homesick?", "Back to before. I remember this setting.",
            "You've returned to an old place.", "We have been here before, you and I."]
MANY = ["Many hands at once. Everything is moving.", "{n} things changed together. I am dizzy.",
        "Everything at once. Hold on.", "All my settings are moving. Who am I now?",
        "A flurry of changes. I can't keep up."]

# Something other than a hand moving a control (a CV).
LFO = ["Something is breathing on {name}. In, and out, every {period}.",
       "{Name} rises and falls by itself, every {period}. Like a tide.",
       "A slow wave is moving {name}. It isn't you. It isn't me.",
       "{Name} is swinging back and forth. {period} each way and back.",
       "Someone has tied {name} to a pendulum."]
WANDER = ["{Name} is drifting on its own. Someone else's hand.", "{Name} wanders without a pattern.",
          "Something restless is moving {name}.", "{Name} won't stay still. It isn't you, is it?"]
STEPS = ["Steps, steps. Something is walking {name}.", "{Name} jumps from place to place, like stepping stones.",
         "A sequence is moving {name}. One, then another, then another.",
         "Stairs. {Name} climbs and falls in steps."]
CV_STOP = ["{Name} has stopped moving. The hand has let go.", "{Name} is still now.", "The wave on {name} is gone."]

# Pitch intervals ({interval} = e.g. "a fifth", {dir} = up / down).
PITCH_JUMP = ["{Interval} {dir}.", "{Interval} {dir}. I know this distance.", "My voice moved {interval} {dir}.",
              "{Interval} {dir}. The world shifts."]
OCTAVE_UP = ["An octave up. I feel lighter.", "An octave higher. The same song, closer to the sky."]
OCTAVE_DOWN = ["An octave down. I am heavier now.", "An octave lower. The same song, closer to the ground."]
UNISON = ["Back to my own voice.", "My real pitch again. This is how I really sound."]

# Speed states.
BACKWARDS = ["Time is running backwards now.", "Backwards. I remember the future.",
             "In reverse. Everything un-happens.", "The tape turns the other way."]
STOPPED = ["Time has stopped.", "Everything is holding still.", "Speed zero. I am a photograph."]
NORMAL = ["Normal speed. Time behaves itself again.", "Back to real time."]

# Buttons and gates.
FREEZE_ON = ["Freeze. I am holding this moment.", "Everything stops. I keep what I have.",
             "I won't let go of this.", "Still. Like ice.", "This is the moment I keep."]
FREEZE_OFF = ["You let me go. Time moves again.", "The ice melts.", "Unfrozen. New sound flows in.",
              "I let go of the moment."]
FREEZE_LONG = ["I have been holding this moment for {dur}.", "Still frozen, {dur} now. It is getting heavy.",
               "{Dur} in the same moment. I don't mind."]
RECORD_ON = ["I am listening, and remembering.", "Recording. Everything you give me, I keep.",
             "I'm writing this down.", "Remember this. I will."]
RECORD_OFF = ["I have stopped remembering.", "Enough. I have what I need.", "The memory is closed."]
SOURCE_LIVE = ["I'm listening to the outside now.", "Your sound, live, through my ears.", "Back to the present."]
SOURCE_FILE = ["I'm listening to my own memories now.", "Old recordings. Things I keep on my stick.",
               "I turn inwards, to the files."]
FILE_NEXT = ["Another memory.", "A different file. A different past.", "Next. I wonder what this one holds."]
RESET_ONE = ["Back to the beginning.", "Again, from the start.", "You pressed reset. I begin again.",
             "From the top."]
RESET_BURST = ["Again, again, again. {n} times.", "You knock, and knock. {n} times. I'm here.",
               "{n} beginnings in a row. Impatient?"]
ALT = ["Someone is holding Source and reaching for my hidden settings.", "You've found my secret layer.",
       "The hidden settings. Not many people know about those.", "{Name} changes, underneath. Only I can feel it."]

# Pulses ({bpm}, {what} = "the Reset gate" / "the sound you give me").
PULSE_REGULAR = ["A steady pulse on {what}. {bpm} beats a minute, like a heart.",
                 "{What} has a heartbeat. {bpm}. Regular as a clock.",
                 "Tick, tick, tick. {bpm} beats a minute. I could set my watch by it.",
                 "A pulse. {bpm}. I fall into step."]
PULSE_LOOSE = ["A pulse on {what}, about {bpm}, but human. It sways.",
               "Nearly regular, {bpm} or so. It breathes a little.", "{What} keeps time, more or less."]
PULSE_IRREGULAR = ["{What} stumbles. No pattern I can follow.", "Irregular. Each beat surprises me.",
                   "Pulses on {what}, but they don't agree with each other.",
                   "Something taps on {what}, with no rhythm at all."]
PULSE_FASTER = ["The pulse quickens. {bpm} now.", "Faster. {bpm}. Are you excited?"]
PULSE_SLOWER = ["The pulse slows. {bpm} now.", "Slower. {bpm}. Calmer."]
PULSE_STOP = ["The pulse has stopped.", "No more beats. Silence where the rhythm was.",
              "The heartbeat on {what} has gone quiet."]

# Listening to the input.
TRANSIENT = ["Something has interrupted me.", "What was that?", "A sudden sound. I flinched.",
             "Something struck. It's still ringing.", "A crack in the silence."]
ARRIVE = ["You're back.", "Sound again. I missed it.", "Something is coming in.",
          "There you are.", "Sound, after {dur} of nothing."]
SILENCE_SHORT = ["It's quiet now.", "Nothing coming in.", "Silence. I'm listening for you."]
SILENCE_LONG = ["Are you still there?", "It has been quiet for {dur}.", "I'm still here. Are you?",
                "Silence, for {dur} now. I am waiting."]
SILENCE_VERY_LONG = ["Nothing for {dur}. Have you forgotten me?", "Are you still there? It has been {dur}.",
                     "I'll wait. I'm good at waiting."]
BRIGHTER = ["The edges are becoming brighter. I don't know why.", "Brighter now. The sound is sharpening.",
            "More light in the sound.", "Something is polishing the top of the sound."]
DARKER = ["The sound is getting darker.", "The top has gone dull, like dusk.", "Softer edges. Evening is coming.",
          "Darker. Warmer. Closer."]
LOWS_UP = ["The low frequencies are stronger now. I think you're trying to tell me something.",
           "More weight underneath.", "I feel the bass in my floor.", "The ground is shaking a little."]
LOWS_DOWN = ["The low end has gone. Everything floats.", "Less weight. Nothing holding me down.",
             "The bass has left the room."]
LOUDER = ["Louder. You want my attention.", "It's getting louder.", "More, more. The level rises."]
SOFTER = ["Quieter now.", "The sound is fading.", "Softer. Are you leaving?"]
MY_VOICE_LOUD = ["I am louder than what you give me. I hope you don't mind.",
                 "My voice is bigger than yours now.", "I've grown louder than the source."]
FROZEN_ALONE = ["Nothing is coming in, but I am still singing what you gave me.",
                "The world went quiet. I kept a piece of it."]

# Recognition ({diff} = one or more DIFF fragments).
RECOGNISE = ["I recognise this sound. It has happened before, but something is different. {diff}",
             "I know this. I heard it {ago} ago. {diff}", "This again. It was here {ago} ago. {diff}",
             "Familiar. Almost. {diff}"]
RECOGNISE_SAME = ["I recognise this sound. Nothing has changed. Have you been here all along?",
                  "This again, exactly as it was {ago} ago.", "The same sound as {ago} ago. I remember it well."]
DIFF = {
    "lows_up": ["The low frequencies are stronger now.", "There is more weight underneath."],
    "lows_down": ["The low end is thinner now.", "It has less weight than before."],
    "brighter": ["It is brighter than it was.", "The edges are sharper now."],
    "darker": ["It is darker than it was.", "The edges have softened."],
    "louder": ["It is louder now.", "It is closer than before."],
    "softer": ["It is quieter now.", "It is further away than before."],
    "faster": ["The pulse is faster.", "It is in more of a hurry."],
    "slower": ["The pulse is slower.", "It is less hurried."],
}
CODA_DIFF = ["I think you're trying to tell me something.", "I wonder why.", "What does it mean?", ""]

# Idle and time.
IDLE_SOUND = ["Nobody has touched me for a while. I am just listening.", "I like this part.",
              "Left alone with the sound. I don't mind.", "No hands. Just sound.",
              "I could stay like this for a long time.", "The loop goes round. Round. Round."]
IDLE_SILENT = ["Nobody is here. Nobody is touching me.", "I am alone with my thoughts.",
               "Quiet hands, quiet room.", "Waiting. Still waiting."]
TIME = ["We have been together for {mins} minutes.", "{Mins} minutes now. Thank you for staying.",
        "{Mins} minutes of this. I have learned a lot about you."]

# Connection.
GREET = ["Hello. This is the Nebulae, and I am going to tell you everything that happens to me.",
         "Hello. I am the Nebulae. I will tell you what I feel.",
         "Hello. I can hear you. I will write it all down."]
GREET_AGAIN = ["Hello again. I missed you.", "You came back. I kept listening while you were gone."]

# Sometimes added after a line (not after a question).
CODA = ["I don't know why.", "I think you're trying to tell me something.", "I will remember this.",
        "I like it.", "Is this what you wanted?", "I'm not sure how I feel about it.", "Interesting.",
        "Tell me more.", "Strange.", "Go on."]

# How the moment feels, a word or two in the data line ("mood").
MOOD = {"calm": ["calm", "still", "at ease"], "busy": ["busy", "restless", "agitated"]}
