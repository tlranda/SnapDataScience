# SNAP Data Science

So far we're just a simple python3 script that analyzes an overly-specific CSV format where each row represents a single match:

date|my deck|player|locations|cards|outcome|cubes|bot behavior?|deck archetype|archetype certain

In short:

* date: In the format of MM/DD/YYYY
* my deck: String representing your queued deck name
* player: Your opponent's name
* locations: Double-quoted string with commas separating location names
* cards: Double-quoted string with commas separating card names (ONLY deck-included cards)
* outcome: String from: "opp retreat" if opponent retreats, "retreat" if you retreat, "resolve" if the game ends normally
* cubes: Positive or negative integer representing cube change
* bot behavior?: String "yes" or "no" for whether you suspect this match was against a bot
* deck archetype: String representing the archetype you believe the opponent ran
* archetype certain: String "yes" or "no" for how positive you are that the deck archetype identification is accurate

ALL location and card names should have NEITHER SPACES, PUNCTUATION, NOR CAPITALIZATION

The script includes `--help` via Python3-ArgParse so you can learn how to use the script in that way.

