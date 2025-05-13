import streamlit as st
from PlaceFinder import PlaceFinder # Assuming PlaceFinder.py is in the same directory
import pandas as pd # Import pandas for DataFrame
from annotated_text import annotated_text # Import annotated_text
import re # Import re for regex replacement

# Set page config to wide layout
st.set_page_config(layout="wide")

# Initialize PlaceFinder
finder = PlaceFinder()

st.title("Place Finder")

st.sidebar.header("About")
st.sidebar.info("This app uses a simple DFA-based approach to identify potential place names in text.")

st.header("Input Text")
text_input = st.text_area("Enter text to analyze:", height=200, placeholder="E.g., I went to San Francisco. Then I visited New York City.")

if st.button("Find Places"):
    if text_input:
        with st.spinner("Processing..."):
            results = finder.find_places(text_input)
            logs = finder.get_logs()
            pos_tags_lines = finder.get_pos_tags_lines()

        st.header("Results")
        if results:
            # Add highlighted text section
            st.subheader("Text with Identified Places:")
            
            # --- New highlighting logic to prevent incorrect nested bolding ---
            potential_highlights = []
            # Sort place names by length (longest first) to use as a priority metric.
            # This helps decide which rule wins if multiple rules match the same text span.
            sorted_place_names_for_rules = sorted(results.keys(), key=len, reverse=True)

            for place_name_rule in sorted_place_names_for_rules:
                place_escaped = re.escape(place_name_rule)
                for match in re.finditer(place_escaped, text_input, flags=re.IGNORECASE):
                    potential_highlights.append({
                        'start': match.start(),
                        'end': match.end(),
                        'text': match.group(0),  # Use text exactly as it appeared in input
                        'priority': len(place_name_rule) # Length of the rule
                    })
            
            # Sort all found highlights:
            # Primary sort key: start index (ascending).
            # Secondary sort key: priority (length of rule, descending - longest rule wins).
            potential_highlights.sort(key=lambda h: (h['start'], -h['priority']))
            
            actual_highlights = []
            last_highlight_end_pos = -1
            for highlight in potential_highlights:
                # Add highlight if it dzaoesn't overlap with the previous chosen one
                # (i.e., it starts at or after the last one ended)
                if highlight['start'] >= last_highlight_end_pos:
                    actual_highlights.append(highlight)
                    last_highlight_end_pos = highlight['end']
                # Implicitly, if highlight['start'] < last_highlight_end_pos, it's an overlap.
                # Because of the sort order (start, -priority), we've already chosen the
                # "best" (longest rule) highlight for the region starting before or at highlight['start']
                # that might overlap. So, overlapping shorter/later-in-sort highlights are skipped.

            # actual_highlights is now a list of non-overlapping, highest-priority highlights,
            # already sorted by start position.
            
            # Construct the final text with markdown bolding
            highlighted_parts = []
            current_pos = 0
            for highlight in actual_highlights:
                # Append text before the current highlight
                if highlight['start'] > current_pos:
                    highlighted_parts.append(text_input[current_pos:highlight['start']])
                
                # Append the bolded place (using original matched text for casing)
                highlighted_parts.append(f"**{highlight['text']}**")
                current_pos = highlight['end']
            
            # Append any remaining text after the last highlight
            if current_pos < len(text_input):
                highlighted_parts.append(text_input[current_pos:])
            
            highlighted_text = "".join(highlighted_parts)
            # --- End of new highlighting logic ---
            
            st.markdown(highlighted_text)     
                   
            st.subheader("Identified Place Candidates & Counts:")
            for place, count in results.items():
                st.write(f"- **{place}**: {count}")
        else:
            st.write("No place candidates found.")

        with st.expander("View Part-of-Speech Tags", expanded=True):
            st.subheader("Part-of-Speech Tags") # Updated subheader
            for i, line_tags in enumerate(pos_tags_lines):
                if line_tags:
                    elements_for_annotated_text = []
                    for token, tag in line_tags:
                        # Define symbols that should be plain text
                        if token in ['.', ',', '(', ')', '[', ']', '{', '}', ':', ';', '"', "'", '!', '?', '-', '--']:
                            elements_for_annotated_text.append((token, " ")) 
                        else:
                            # Word and its tag for annotation
                            # Escape '$' to prevent KaTeX interpretation issues
                            safe_tag = tag.replace('$', '\\$') # Escape backslash for string literal, then escape $ for KaTeX
                            elements_for_annotated_text.append((token, safe_tag)) 
                            elements_for_annotated_text.append(" ") 
                    
                    if elements_for_annotated_text:
                        # Pass all elements as *args to annotated_text
                        # It will add spaces between them automatically.
                        annotated_text(*elements_for_annotated_text)
                else:
                    st.write("_Original line was empty or contained no processable tokens._")
            st.caption("Raw POS tags data (for debugging):")
            st.json([{"line_number": i+1, "tags": tags} for i, tags in enumerate(pos_tags_lines)], expanded=False)


        with st.expander("View DFA State Transitions Log", expanded=True):
            st.subheader("DFA Processing Log")
            
            # Filter logs for character processing and state changes
            # Adapt this to match the new log format from character-based DFA
            transition_logs = [
                log for log in logs 
                if "char" in log and "prev_state" in log and "new_state" in log and "action" in log
            ]
            
            if transition_logs:
                # Convert to DataFrame for better display
                df_transitions = pd.DataFrame(transition_logs)
                # Select and reorder columns for clarity
                df_display = df_transitions[["char", "prev_state", "action", "new_state", "buffer", "word_buffer"]]
                df_display.columns = ["Character", "Previous State", "Action/Details", "New State", "Current Buffer", "Word Buffer"]
                st.dataframe(df_display, use_container_width=True)
            else:
                st.write("No detailed DFA transition logs available (or logs are not in the expected format).")
        
            st.caption("Full Raw Logs (for debugging):")
            st.json(logs)
        
        # Remove the old expanders if they are now redundant or re-purpose them
        # The old "View Processing Logs" and "View Part-of-Speech Tags (by line)" are replaced by the above.

    else:
        st.warning("Please enter some text to analyze.")

st.sidebar.header("How it Works (Simplified)")
st.sidebar.markdown("""
- The text is tokenized and tagged for parts of speech (POS).
- A Deterministic Finite Automaton (DFA) processes these tokens.
- It looks for capitalized words (Proper Nouns, Nouns) that might be part of a place name.
- It handles prepositions (e.g., "in", "at") that might precede a place.
- It allows for connecting words like "of", "the", "and" within place names.
- Finally, it post-processes candidates to filter out common words or unlikely sequences.
""")

# To run this app:
# 1. Make sure you have streamlit installed: pip install streamlit
# 2. Navigate to this directory in your terminal.
# 3. Run: streamlit run app.py
