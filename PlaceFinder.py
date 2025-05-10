import re
import nltk
from nltk import pos_tag
from nltk.tokenize import word_tokenize, sent_tokenize

# Uncomment to download required NLTK data (run once)
# nltk.download('punkt')
# nltk.download('averaged_perceptron_tagger')

# Common words to exclude as standalone place names
COMMON_WORDS_EXCLUSION_SET = {
    "The", "Is", "And", "Or", "But", "A", "An", "Of", "To", "In", "On", "At", "For", "With", "By", "From",
    "He", "She", "It", "They", "We", "You", "I",
    "His", "Her", "Its", "Their", "Our", "Your", "My",
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "Mr", "Mrs", "Ms", "Dr"
}

# Character-based DFA States
S_START = "START"             # Initial state
S_CAPITAL = "CAPITAL"         # Seen a capital letter (potential start of place)
S_IN_WORD = "IN_WORD"         # Inside a word that may be part of a place name
S_SPACE = "SPACE"             # Space after a word in potential place name
S_CONNECTING = "CONNECTING"   # In a connecting word (of, the, and)

# Connecting words that can appear within place names
CONNECTING_WORDS = {"of", "the", "and", "for"}

# Prepositions that might precede a place name
PREPOSITIONS = {"in", "on", "at", "to", "from", "with", "by", "near", "towards", "unto"}


class PlaceFinder:
    def __init__(self):
        self.current_state = S_START
        self.current_buffer = ""      # Buffer for accumulating characters
        self.word_buffer = []         # Buffer for accumulating words
        self.connecting_buffer = ""   # Buffer for potential connecting word
        self.raw_candidates = []
        self.logs = []
        self.pos_tags_lines = []      # Now will store actual POS tags
        self.token_tag_map = {}       # Map tokens to their POS tags

    def _perform_pos_tagging(self, text):
        """Process text with NLTK to generate POS tags"""
        self.pos_tags_lines = []
        self.token_tag_map = {}
        
        # Split text into sentences
        sentences = sent_tokenize(text)
        
        for sentence in sentences:
            # Tokenize and tag
            tokens = word_tokenize(sentence)
            tagged = pos_tag(tokens)
            self.pos_tags_lines.append(tagged)
            
            # Build token to tag map for quick lookup
            for token, tag in tagged:
                # If token appears multiple times with different tags, prioritize proper noun tags
                if token in self.token_tag_map and tag.startswith('NNP'):
                    self.token_tag_map[token] = tag
                elif token not in self.token_tag_map:
                    self.token_tag_map[token] = tag
            
        self.logs.append({"event": "POS_Tagging", "detail": f"Generated POS tags for {len(sentences)} sentences"})
        return self.pos_tags_lines

    def _is_potential_place_token(self, token, tag=None):
        """Checks if a token could be part of a place name."""
        if not token:
            return False
            
        # If no tag provided, look up in our map
        if tag is None:
            tag = self.token_tag_map.get(token)
            # If token not found in map, fall back to capitalization check
            if tag is None:
                return token[0].isupper() and len(token) > 1
        
        # Must be capitalized and a relevant noun type (Proper Noun, or general Noun)
        return token[0].isupper() and tag in ['NNP', 'NNPS', 'NN', 'NNS']

    def _log_char_action(self, char, prev_state, action, new_state):
        """Log character transitions for debugging"""
        log_entry = {
            "char": char,
            "prev_state": prev_state,
            "action": action,
            "new_state": new_state,
            "buffer": self.current_buffer,
            "word_buffer": " ".join(self.word_buffer)
        }
        self.logs.append(log_entry)

    def _finalize_candidate(self):
        """Add current word to word buffer and reset state"""
        # Add last word if not empty (and not already added to word_buffer)
        if self.current_buffer:
            self.word_buffer.append(self.current_buffer)
            self.current_buffer = ""
            
        # Create candidate from word buffer if not empty
        if self.word_buffer:
            candidate = " ".join(self.word_buffer)
            self.raw_candidates.append(candidate)
            result = f"Finalized candidate: '{candidate}'"
        else:
            result = "No words in buffer to finalize"
            
        # Reset buffers
        self.current_buffer = ""
        self.word_buffer = []
        self.connecting_buffer = ""
        
        return result

    def process_char(self, char):
        """Process a single character through the automaton"""
        prev_state = self.current_state
        action = ""
        
        # Consider newlines as spaces for state transition purposes
        is_space_like = char.isspace() or char == '\n' or char == '\r'
        
        # Handle character based on current state
        if self.current_state == S_START:
            if char.isupper():
                self.current_buffer = char
                self.current_state = S_CAPITAL
                action = f"Started potential place with capital letter: '{char}'"
            elif char.islower() and not self.connecting_buffer:
                self.connecting_buffer = char
                action = f"Potential connecting/preposition word started: '{char}'"
            elif char.islower() and self.connecting_buffer:
                self.connecting_buffer += char
                action = f"Continuing potential connecting/preposition word: '{self.connecting_buffer}'"
            elif is_space_like and self.connecting_buffer:
                # Check if connecting buffer is a preposition
                if self.connecting_buffer.lower() in PREPOSITIONS:
                    action = f"Found preposition '{self.connecting_buffer}', watching for place"
                self.connecting_buffer = ""
            else:
                action = f"Ignoring character: '{char}'"                
        elif self.current_state == S_CAPITAL:
            if char.isalpha():
                self.current_buffer += char
                self.current_state = S_IN_WORD
                action = f"Continuing word: '{self.current_buffer}'"
            elif char.isspace():
                self.word_buffer.append(self.current_buffer)
                self.current_buffer = ""
                self.current_state = S_SPACE
                action = f"End of first word, now in space after '{self.word_buffer[-1]}'"
            else:
                # Non-alphabetic char breaks the sequence
                if len(self.current_buffer) > 1:  # Only keep if word is more than 1 char
                    self.word_buffer.append(self.current_buffer)
                    result = self._finalize_candidate()
                    action = f"Non-alphabet char '{char}' encountered. {result}"
                else:
                    action = f"Discarding single letter '{self.current_buffer}' due to non-alphabet char '{char}'"
                self.current_buffer = ""
                self.current_state = S_START
                
        elif self.current_state == S_IN_WORD:
            if char.isalpha():
                self.current_buffer += char
                action = f"Continuing word: '{self.current_buffer}'"
            elif is_space_like:
                self.word_buffer.append(self.current_buffer)
                self.current_buffer = ""
                self.current_state = S_SPACE
                action = f"End of word, now in space after '{self.word_buffer[-1]}'"
            else:
                # Non-alphabetic char breaks the sequence
                if self.current_buffer:  # Only process if buffer has content
                    self.word_buffer.append(self.current_buffer)
                    self.current_buffer = "" # Clear this to avoid duplication in _finalize_candidate
                    result = self._finalize_candidate()
                    action = f"Non-alphabet char '{char}' encountered. {result}"
                else:
                    action = f"Empty buffer with non-alphabet char '{char}'"
                self.current_buffer = ""
                self.current_state = S_START     
                           
        elif self.current_state == S_SPACE:
            if char.isupper():
                self.current_buffer = char
                self.current_state = S_CAPITAL
                action = f"New capitalized word started: '{char}'"
            elif char.islower():
                self.connecting_buffer = char
                self.current_state = S_CONNECTING
                action = f"Potential connecting word started: '{char}'"
            elif char.isspace():
                action = "Multiple spaces - still in space state"
            else:
                # Punctuation or other non-alphabetic char ends the sequence
                result = self._finalize_candidate()
                self.current_state = S_START
                action = f"Punctuation or non-alphabet char '{char}' ends sequence. {result}"
                
        elif self.current_state == S_CONNECTING:
            if char.isalpha():
                self.connecting_buffer += char
                action = f"Continuing connecting word: '{self.connecting_buffer}'"
            elif char.isspace():
                # Check if it's a valid connecting word
                if self.connecting_buffer.lower() in CONNECTING_WORDS:
                    self.word_buffer.append(self.connecting_buffer)
                    action = f"Valid connecting word '{self.connecting_buffer}' added to place"
                    self.current_state = S_SPACE
                else:
                    # Not a connecting word, so finalize candidate and reset
                    result = self._finalize_candidate()
                    self.current_state = S_START
                    action = f"Non-connecting word '{self.connecting_buffer}' breaks sequence. {result}"
                self.connecting_buffer = ""
            else:
                # Non-alphabetic char breaks the sequence
                result = self._finalize_candidate()
                self.current_state = S_START
                self.connecting_buffer = ""
                action = f"Non-alphabet char '{char}' ends sequence. {result}"
        
        self._log_char_action(char, prev_state, action, self.current_state)
    
    def find_places(self, text):
        """Process the entire text character by character"""
        # Run POS tagging first so we can validate with it later
        self._perform_pos_tagging(text)
        
        self.current_state = S_START
        self.current_buffer = ""
        self.word_buffer = []
        self.connecting_buffer = ""
        self.raw_candidates = []
        self.logs.append({"event": "ProcessStart", "detail": "Starting character-based DFA processing"})
        
        # Process each character
        for char in text:
            self.process_char(char)
            
        # End of text - check if we need to finalize a candidate
        if self.current_state in [S_CAPITAL, S_IN_WORD, S_SPACE, S_CONNECTING]:
            if self.current_buffer:
                self.word_buffer.append(self.current_buffer)
            if self.connecting_buffer and self.connecting_buffer.lower() in CONNECTING_WORDS:
                self.word_buffer.append(self.connecting_buffer)
            
            if self.word_buffer:
                result = self._finalize_candidate()
                self._log_char_action("<<EOF>>", self.current_state, 
                                     f"End of text. {result}", S_START)
                
        return self.post_process_candidates()
    
    def post_process_candidates(self):
        """Filter the raw candidates to remove unlikely place names"""
        processed_candidates = []
        self.logs.append({"event": "PostProcessingStart", "detail": f"Raw candidates: {self.raw_candidates}"})
        
        for candidate in self.raw_candidates:
            # Check for duplicate words (e.g., "Singapore Singapore")
            words = candidate.split()
            if len(words) > 1 and len(set(words)) < len(words):
                self.logs.append({"event": "PostProcessFilter", "candidate": candidate, 
                                 "filter_type": "DuplicateWords", 
                                 "detail": f"Detected repeated words in '{candidate}'"})
                # Skip to next candidate if there are duplicates
                continue
                
            # Length Filter
            if len(candidate) < 2:
                self.logs.append({"event": "PostProcessFilter", "candidate": candidate, 
                                  "filter_type": "Length", "detail": "Filtered (length < 2)."})
                continue

            # Common Words Filter (whole candidate, if it's a single word)
            words_in_candidate = candidate.split(' ')
            if len(words_in_candidate) == 1 and candidate in COMMON_WORDS_EXCLUSION_SET:
                self.logs.append({"event": "PostProcessFilter", "candidate": candidate, 
                                 "filter_type": "CommonWord", "detail": "Filtered (single common word)."})
                continue

            # First Word Filter
            if len(words_in_candidate) > 1 and words_in_candidate[0] in COMMON_WORDS_EXCLUSION_SET:
                # Allow if the common word is "The" and the place name is likely significant
                if not (words_in_candidate[0].lower() == "the" and len(words_in_candidate) > 1):
                    self.logs.append({"event": "PostProcessFilter", "candidate": candidate,
                                     "filter_type": "FirstWordCommon", 
                                     "detail": f"Filtered (common first word: '{words_in_candidate[0]}')."})
                    continue
            
            # Last Word Filter (if last word is a common connecting word)
            if len(words_in_candidate) > 1 and words_in_candidate[-1].lower() in CONNECTING_WORDS:
                self.logs.append({"event": "PostProcessFilter", "candidate": candidate,
                                 "filter_type": "LastWordConnector", 
                                 "detail": f"Filtered (ends with connector: '{words_in_candidate[-1]}')."})
                continue
            
            # POS Tag Validation - verify if main words in candidate are proper nouns
            valid_place = False
            for word in words_in_candidate:
                # Skip connecting words
                if word.lower() in CONNECTING_WORDS:
                    continue
                    
                # Check if it's a potential place name token
                if self._is_potential_place_token(word):
                    valid_place = True
                    break
            
            if not valid_place:
                self.logs.append({"event": "PostProcessFilter", "candidate": candidate,
                                 "filter_type": "POSTaggingCheck", 
                                 "detail": f"Filtered (no proper noun tokens in '{candidate}')."})
                continue

            processed_candidates.append(candidate)

        # Count occurrences of each candidate
        candidate_counts = {}
        for pc in processed_candidates:
            candidate_counts[pc] = candidate_counts.get(pc, 0) + 1
        
        self.logs.append({"event": "PostProcessingEnd", "final_candidates_counts": candidate_counts})
        return candidate_counts

    def get_logs(self):
        return self.logs

    def get_pos_tags_lines(self):
        """Return the POS-tagged lines"""
        return self.pos_tags_lines