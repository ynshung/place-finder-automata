# Define states for clarity
STATE_START = 0
STATE_IN_WORD = 1  # Accepting state (if followed by delimiter or invalid char after space)
STATE_EXPECT_CAPITAL_AFTER_SPACE = 2

# Define character categories
CAT_UPPER = 'UPPER'
CAT_LOWER = 'LOWER'
CAT_SPACE = 'SPACE'
CAT_DELIMITER = 'DELIMITER' # Includes punctuation, digits, newline, etc.

# --- Refinement: Define common words to exclude ---
# Common English words often capitalized at sentence start, unlikely place names.
# Also includes single letters often capitalized.
COMMON_WORDS_EXCLUSION_SET = {
    "I", "He", "She", "It", "We", "They",
    "The", "A", "An",
    "This", "That", "These", "Those",
    "On", "In", "At", "For", "With", "By", "From", "To",
    "And", "Or", "But", "So", "If", "When", "While", "Although", "Because",
    "Is", "Are", "Was", "Were", "Be", "Been", "Being", "Have", "Has", "Had",
    "Do", "Does", "Did",
    "Then", "Now", "Here", "There",
    "What", "Who", "Where", "Why", "How", "Since"
}

def get_char_category(char):
    """Categorizes a character for the DFA."""
    if char.isupper():
        return CAT_UPPER
    elif char.islower():
        return CAT_LOWER
    elif char == ' ':
        return CAT_SPACE
    else:
        # Treat anything else (punctuation, digits, control chars) as a delimiter
        return CAT_DELIMITER


def find_places_name(text, output_file):
    """
    Recognizes potential place names using a DFA simulation and then filters
    out common words and single characters.

    Args:
        text (str): The input text potentially containing place names.

    Returns:
        list: A list of unique potential place names found after filtering.
    """
    # --- DFA Initialization ---
    current_state = STATE_START
    # Store all potential candidates first, including common words/single chars
    potential_candidates = []
    current_potential_place = ""

    # Add a delimiter at the end to ensure the last word is processed
    processed_text = text + "\n"

    output_file.write("--- DFA Simulation Trace ---" + "\n")
    output_file.write(f"{'Char':<5} | {'Category':<10} | {'State Before':<12} | {'Action':<55} | {'State After':<12} | {'Buffer'}" + "\n")
    output_file.write("-" * 110 + "\n")

    # --- Process Character by Character (DFA Simulation) ---
    for char in processed_text:
        category = get_char_category(char)
        state_before = current_state
        action_taken = "None"

        # --- State Transition Logic ---
        if current_state == STATE_START:
            if category == CAT_UPPER:
                current_state = STATE_IN_WORD
                current_potential_place += char
                action_taken = f"Start potential candidate: '{char}'"
            else:
                action_taken = "Ignoring char, not starting candidate"
                current_state = STATE_START
                current_potential_place = ""

        elif current_state == STATE_IN_WORD:
            if category == CAT_UPPER or category == CAT_LOWER:
                current_state = STATE_IN_WORD
                current_potential_place += char
                action_taken = f"Append letter: '{char}'"
            elif category == CAT_SPACE:
                current_state = STATE_EXPECT_CAPITAL_AFTER_SPACE
                current_potential_place += char
                action_taken = f"Append space, expecting capital: '{char}'"
            elif category == CAT_DELIMITER:
                # --- Potential Acceptance Case 1 ---
                if current_potential_place:
                     if char == '\n':
                         action_taken = f"Newline '\\n' found. Potential candidate: '{current_potential_place}'"
                     else:
                         action_taken = f"Delimiter '{char}' found. Potential candidate: '{current_potential_place}'"
                     if current_potential_place not in potential_candidates:
                         potential_candidates.append(current_potential_place)
                else:
                     if char == '\n':
                         action_taken = f"Newline '\\n' found. Buffer empty."
                     else:
                         action_taken = f"Delimiter '{char}' found. Buffer empty."
                current_state = STATE_START
                current_potential_place = ""
            else:
                 action_taken = f"Unexpected category '{category}' in STATE_IN_WORD. Resetting."
                 current_state = STATE_START
                 current_potential_place = ""


        elif current_state == STATE_EXPECT_CAPITAL_AFTER_SPACE:
            if category == CAT_UPPER:
                current_state = STATE_IN_WORD
                current_potential_place += char
                action_taken = f"Append capital after space: '{char}'"
            else:
                # --- Potential Acceptance Case 2 ---
                place_to_add = current_potential_place.rstrip(' ')
                if place_to_add:
                    action_taken = f"Non-capital '{char}' after space. PC: '{place_to_add}'"
                    if place_to_add not in potential_candidates:
                        potential_candidates.append(place_to_add)
                else:
                     action_taken = f"Non-capital '{char}' after space. Buffer empty before space."

                current_state = STATE_START
                current_potential_place = ""
                # Re-evaluate the current character from the START state
                if category == CAT_UPPER:
                    current_state = STATE_IN_WORD
                    current_potential_place += char
                    action_taken += f" | Re-eval '{char}': Start new candidate."
                else:
                    action_taken += f" | Re-eval '{char}': Ignore, reset."

        # Write trace information to the output file
        state_map = {0: "START", 1: "IN_WORD", 2: "EXPECT_CAS"}
        output_file.write(f"{repr(char):<5} | {category:<10} | {state_map[state_before]:<12} | {action_taken:<55} | {state_map[current_state]:<12} | '{current_potential_place}'" + "\n")

    output_file.write("-" * 110 + "\n")
    output_file.write("--- DFA Simulation End ---" + "\n")
    output_file.write(f"Potential Candidates Found by DFA: {potential_candidates}" + "\n")

    # --- Post-Processing Filter ---
    final_places = []
    for candidate in potential_candidates:
        # Filter 1: Minimum length (e.g., > 1 character)
        if len(candidate) <= 1:
            output_file.write(f"Filtering out '{candidate}': Too short." + "\n")
            continue
        # Filter 2: Check against common word exclusion list
        # Check the whole candidate first (e.g. "Pizza Hut")
        # Then check the first word if it's multi-word (e.g., check "Then" in "Then I")
        first_word = candidate.split(' ', 1)[0]
        if candidate in COMMON_WORDS_EXCLUSION_SET:
             output_file.write(f"Filtering out '{candidate}': Found in common words list." + "\n")
             continue
        # Special check for cases like "Then I", "Or San Francisco" where the *first* word is common
        if ' ' in candidate and first_word in COMMON_WORDS_EXCLUSION_SET:
             output_file.write(f"Filtering out '{candidate}': First word '{first_word}' is common." + "\n")
             continue

        # If not filtered out, add to final list
        if candidate not in final_places: # Ensure uniqueness in final list too
            final_places.append(candidate)

    output_file.write("--- Filtering Complete ---" + "\n")
    return final_places
