import nltk

# Download necessary NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('punkt')
try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except nltk.downloader.DownloadError:
    nltk.download('averaged_perceptron_tagger')


COMMON_WORDS_EXCLUSION_SET = {
    "The", "Is", "And", "Or", "But", "A", "An", "Of", "To", "In", "On", "At", "For", "With", "By", "From",
    "He", "She", "It", "They", "We", "You", "I",
    "His", "Her", "Its", "Their", "Our", "Your", "My",
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "Mr", "Mrs", "Ms", "Dr"
}

# DFA States (Token-based)
S_START = "S_START"
S_IN_PLACE = "S_IN_PLACE"  # Accumulating a potential place name
S_AFTER_PREP = "S_AFTER_PREP"  # Seen a preposition, expecting a place name

# Prepositions that might precede a place name
PREPOSITIONS = {"in", "on", "at", "to", "from", "with", "by", "near", "towards", "unto"}


class PlaceFinder:
    def __init__(self):
        self.current_state = S_START
        self.current_buffer = []  # Stores tokens for the current potential place name
        self.raw_candidates = []
        self.logs = []
        self.pos_tags_lines = [] # Stores list of lists: [[(token, tag), ...], ...]
        self.last_preposition = None # Stores the last seen preposition token

    def _is_potential_place_token(self, token, tag):
        """Checks if a token could be part of a place name."""
        if not token:
            return False
        # Must be capitalized and a relevant noun type (Proper Noun, or general Noun)
        return token[0].isupper() and tag in ['NNP', 'NNPS', 'NN', 'NNS']

    def _is_connecting_word(self, token, tag):
        """Checks for words like 'of', 'the', 'and' that can connect parts of a place name."""
        # Tag 'IN' for 'of', 'DT' for 'the', 'CC' for 'and'
        return token.lower() in {"of", "the", "and", "for"} and tag in ['IN', 'DT', 'CC']


    def _log_token_action(self, token, tag, prev_state, action, new_state):
        log_entry = {
            "token": token,
            "tag": tag,
            "prev_state": prev_state,
            "action": action,
            "new_state": new_state,
            "buffer_after_action": " ".join(self.current_buffer)
        }
        self.logs.append(log_entry)

    def _finalize_candidate(self):
        """Finalizes the current buffer into a raw candidate if it's not empty."""
        if self.current_buffer:
            candidate_str = " ".join(self.current_buffer)
            # Avoid adding single common connecting words if they somehow end up alone
            if len(self.current_buffer) == 1 and self.current_buffer[0].lower() in {"of", "the", "and", "for"}:
                 self.current_buffer = []
                 return f"Discarded lone connecting word: '{candidate_str}'."

            self.raw_candidates.append(candidate_str)
            self.current_buffer = []
            return f"Finalized candidate: '{candidate_str}'."
        self.current_buffer = [] # Ensure buffer is cleared even if it was empty
        return "Buffer was empty, nothing to finalize."

    def process_token_tag(self, token, tag):
        prev_state = self.current_state
        action_summary = ""

        if self.current_state == S_START:
            if self._is_potential_place_token(token, tag):
                self.current_buffer = [token]
                self.current_state = S_IN_PLACE
                action_summary = f"Started place: '{token}' ({tag})."
            elif token.lower() in PREPOSITIONS and tag == 'IN':
                self.current_state = S_AFTER_PREP
                self.last_preposition = token
                action_summary = f"Preposition '{token}' ({tag}). Expecting place."
            else:
                action_summary = f"Ignoring token '{token}' ({tag})."

        elif self.current_state == S_IN_PLACE:
            if self._is_potential_place_token(token, tag):
                self.current_buffer.append(token)
                action_summary = f"Appended to place: '{token}' ({tag})."
            elif self._is_connecting_word(token, tag) and self.current_buffer:
                self.current_buffer.append(token)
                action_summary = f"Appended connecting word: '{token}' ({tag})."
            else: # Token breaks the current place sequence
                finalize_log_msg = self._finalize_candidate() # Clears buffer
                self.current_state = S_START # Reset state
                action_summary = f"{finalize_log_msg} Sequence broken by '{token}' ({tag}). Re-evaluating from S_START: "

                # Re-evaluate current token from S_START
                if self._is_potential_place_token(token, tag):
                    self.current_buffer = [token]
                    self.current_state = S_IN_PLACE
                    action_summary += f"Started new place: '{token}' ({tag})."
                elif token.lower() in PREPOSITIONS and tag == 'IN':
                    self.current_state = S_AFTER_PREP
                    self.last_preposition = token
                    action_summary += f"Preposition '{token}' ({tag}). Expecting place."
                else:
                    action_summary += f"Ignoring token '{token}' ({tag})."

        elif self.current_state == S_AFTER_PREP:
            if self._is_potential_place_token(token, tag):
                self.current_buffer = [token] # Preposition is not part of the place name itself
                self.current_state = S_IN_PLACE
                action_summary = f"Place '{token}' ({tag}) started after preposition '{self.last_preposition}'."
            else: # Did not find a place token
                action_summary = f"No place found after preposition '{self.last_preposition}'. Token '{token}' ({tag}) broke sequence. Re-evaluating from S_START: "
                self.last_preposition = None # Reset as it wasn't followed by a place
                self.current_state = S_START

                # Re-evaluate current token from S_START
                if self._is_potential_place_token(token, tag):
                    self.current_buffer = [token]
                    self.current_state = S_IN_PLACE
                    action_summary += f"Started new place: '{token}' ({tag})."
                elif token.lower() in PREPOSITIONS and tag == 'IN':
                    self.current_state = S_AFTER_PREP
                    self.last_preposition = token
                    action_summary += f"Preposition '{token}' ({tag}). Expecting place."
                else:
                    action_summary += f"Ignoring token '{token}' ({tag})."
        
        self._log_token_action(token, tag, prev_state, action_summary, self.current_state)

    def find_places(self, text):
        self.current_state = S_START
        self.current_buffer = []
        self.raw_candidates = []
        self.logs = []
        self.pos_tags_lines = []
        self.last_preposition = None

        # Preprocessing: Part-of-speech tagging (line by line)
        lines = text.split('\n')
        for line_text in lines:
            if line_text.strip():
                words = nltk.word_tokenize(line_text)
                tagged_tokens = nltk.pos_tag(words)
                self.pos_tags_lines.append(tagged_tokens)
            else:
                self.pos_tags_lines.append([]) # Preserve empty lines
        
        self.logs.append({"event": "Preprocessing", 
                          "details": "Performed Part-of-Speech tagging line by line.", 
                          "tags_by_line": self.pos_tags_lines}) # Changed key for clarity

        # DFA Processing - iterate through tokens from POS tagging
        for line_of_tags in self.pos_tags_lines:
            if not line_of_tags: # Handle empty lines (originally blank lines in input)
                # An empty line acts as a strong delimiter
                if self.current_state == S_IN_PLACE:
                    finalize_log_msg = self._finalize_candidate()
                    self._log_token_action("<<BLANK_LINE>>", "DELIM", self.current_state, f"Blank line. {finalize_log_msg}", S_START)
                    self.current_state = S_START
                elif self.current_state == S_AFTER_PREP:
                    self._log_token_action("<<BLANK_LINE>>", "DELIM", self.current_state, "Blank line after preposition. Resetting.", S_START)
                    self.current_state = S_START
                    self.last_preposition = None
                continue # Move to the next line

            for token, tag in line_of_tags:
                self.process_token_tag(token, tag)
            
            # End of a non-blank line also acts as a delimiter
            if self.current_state == S_IN_PLACE:
                finalize_log_msg = self._finalize_candidate()
                self._log_token_action("<<EOL>>", "DELIM", self.current_state, f"End of line. {finalize_log_msg}", S_START)
                self.current_state = S_START
            elif self.current_state == S_AFTER_PREP:
                self._log_token_action("<<EOL>>", "DELIM", self.current_state, "End of line after preposition. Resetting.", S_START)
                self.current_state = S_START
                self.last_preposition = None

        # After all lines, one last check (e.g., if text doesn't end with newline)
        if self.current_state == S_IN_PLACE and self.current_buffer:
            finalize_log_msg = self._finalize_candidate()
            self._log_token_action("<<EOF>>", "DELIM", S_IN_PLACE, f"End of text. {finalize_log_msg}", S_START)
            self.current_state = S_START
        elif self.current_state == S_AFTER_PREP: # Should ideally be reset by EOL/EOF
             self._log_token_action("<<EOF>>", "DELIM", S_AFTER_PREP, "End of text after preposition. Resetting.", S_START)
             self.current_state = S_START
             self.last_preposition = None


        return self.post_process_candidates()

    def post_process_candidates(self):
        processed_candidates = []
        self.logs.append({"event": "PostProcessingStart", "detail": f"Raw candidates: {self.raw_candidates}"})
        for candidate in self.raw_candidates:
            # Length Filter
            if len(candidate) < 2 and not (len(candidate.split()) > 1) : # Allow short multi-word like "Of Of" if it passes other filters
                 # More precise length filter: filter out very short single words.
                if len(candidate.split()) == 1 and len(candidate) < 2 : # e.g. "A" if it slipped through
                    self.logs.append({"event": "PostProcessFilter", "candidate": candidate, "filter_type": "Length", "detail": "Filtered (length < 2 for single word)." })
                    continue


            # Common Words Filter (whole candidate, if it's a single word)
            words_in_candidate = candidate.split(' ')
            if len(words_in_candidate) == 1 and candidate in COMMON_WORDS_EXCLUSION_SET:
                self.logs.append({"event": "PostProcessFilter", "candidate": candidate, "filter_type": "CommonWord", "detail": "Filtered (single common word)." })
                continue

            # First Word Filter (if first word of multi-word is common and not something like "The X")
            # This needs to be careful not to filter "The Hague"
            if len(words_in_candidate) > 1 and words_in_candidate[0] in COMMON_WORDS_EXCLUSION_SET:
                # Allow if the common word is "The" and the place name is likely significant
                if not (words_in_candidate[0].lower() == "the" and len(words_in_candidate) > 1):
                    self.logs.append({"event": "PostProcessFilter", "candidate": candidate, "filter_type": "FirstWordCommon", "detail": f"Filtered (common first word: '{words_in_candidate[0]}')." })
                    continue
            
            # Last Word Filter (if last word is a common connecting word like 'of', 'the', 'and')
            if len(words_in_candidate) > 1 and words_in_candidate[-1].lower() in {"of", "the", "and", "for"}:
                self.logs.append({"event": "PostProcessFilter", "candidate": candidate, "filter_type": "LastWordConnector", "detail": f"Filtered (ends with connector: '{words_in_candidate[-1]}')." })
                continue


            processed_candidates.append(candidate)

        candidate_counts = {}
        for pc in processed_candidates:
            candidate_counts[pc] = candidate_counts.get(pc, 0) + 1
        
        self.logs.append({"event": "PostProcessingEnd", "final_candidates_counts": candidate_counts})
        return candidate_counts

    def get_logs(self):
        return self.logs

    def get_pos_tags_lines(self):
        return self.pos_tags_lines

