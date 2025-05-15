import streamlit as st
from PlaceFinder import PlaceFinder
import pandas as pd
from annotated_text import annotated_text 
import re

# Set page config to wide layout
st.set_page_config(layout="wide")

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
            st.subheader("Text with Identified Places:")
            
            potential_highlights = []
            sorted_place_names_for_rules = sorted(results.keys(), key=len, reverse=True)

            for place_name_rule in sorted_place_names_for_rules:
                place_escaped = re.escape(place_name_rule)
                for match in re.finditer(place_escaped, text_input, flags=re.IGNORECASE):
                    potential_highlights.append({
                        'start': match.start(),
                        'end': match.end(),
                        'text': match.group(0),
                        'priority': len(place_name_rule)
                    })
            
            potential_highlights.sort(key=lambda h: (h['start'], -h['priority']))
            
            actual_highlights = []
            last_highlight_end_pos = -1
            for highlight in potential_highlights:
                if highlight['start'] >= last_highlight_end_pos:
                    actual_highlights.append(highlight)
                    last_highlight_end_pos = highlight['end']

            highlighted_parts = []
            current_pos = 0
            for highlight in actual_highlights:
                if highlight['start'] > current_pos:
                    highlighted_parts.append(text_input[current_pos:highlight['start']])
                
                highlighted_parts.append(f"**{highlight['text']}**")
                current_pos = highlight['end']
            
            if current_pos < len(text_input):
                highlighted_parts.append(text_input[current_pos:])
            
            highlighted_text = "".join(highlighted_parts)
            
            st.markdown(highlighted_text)     
                   
            st.subheader("Identified Place Candidates & Counts:")
            for place, count in results.items():
                st.write(f"- **{place}**: {count}")
        else:
            st.write("No place candidates found.")

        with st.expander("View Part-of-Speech Tags", expanded=True):
            st.subheader("Part-of-Speech Tags")
            for i, line_tags in enumerate(pos_tags_lines):
                if line_tags:
                    elements_for_annotated_text = []
                    for token, tag in line_tags:
                        if token in ['.', ',', '(', ')', '[', ']', '{', '}', ':', ';', '"', "'", '!', '?', '-', '--']:
                            elements_for_annotated_text.append((token, " ")) 
                        else:
                            # Word and its tag for annotation
                            # Escape '$' to prevent KaTeX interpretation issues
                            safe_tag = tag.replace('$', '\\$')
                            elements_for_annotated_text.append((token, safe_tag)) 
                            elements_for_annotated_text.append(" ") 
                    
                    if elements_for_annotated_text:
                        annotated_text(*elements_for_annotated_text)
                else:
                    st.write("_Original line was empty or contained no processable tokens._")
            st.caption("Raw POS tags data (for debugging):")
            st.json([{"line_number": i+1, "tags": tags} for i, tags in enumerate(pos_tags_lines)], expanded=False)


        with st.expander("View DFA State Transitions Log", expanded=True):
            st.subheader("DFA Processing Log")
            
            transition_logs = [
                log for log in logs 
                if "char" in log and "prev_state" in log and "new_state" in log and "action" in log
            ]
            
            if transition_logs:
                df_transitions = pd.DataFrame(transition_logs)
                df_display = df_transitions[["char", "prev_state", "action", "new_state", "buffer", "word_buffer"]]
                df_display.columns = ["Character", "Previous State", "Action/Details", "New State", "Current Buffer", "Word Buffer"]
                st.dataframe(df_display, use_container_width=True)
            else:
                st.write("No detailed DFA transition logs available (or logs are not in the expected format).")
        
            st.caption("Full Raw Logs (for debugging):")
            st.json(logs)

    else:
        st.warning("Please enter some text to analyze.")

st.sidebar.header("How it Works (Simplified)")
st.sidebar.markdown("""
- A character-based Deterministic Finite Automaton (DFA) then processes the text character by character:
    - It looks for sequences typically starting with a capital letter, accumulating characters to form words.
    - It transitions between states like `START`, `CAPITAL` (first capital letter seen), `IN_WORD` (accumulating a word), `SPACE` (after a word), and `CONNECTING` (handling specific connecting words like "of", "the", "and", "for").
    - When a potential place name sequence is broken (e.g., by punctuation, a non-connecting lowercase word, or end of text), the accumulated words are considered candidates.
- These raw candidates are then post-processed:
    - Candidates with repeated words (e.g., "Place Place") are filtered out.
    - Short candidates (less than 2 characters) are removed.
    - Single common words (e.g., "The", "Is", months, days) are filtered out if they appear as standalone candidates.
    - Candidates starting with a common word (unless it's "The" followed by other words) or ending with a connecting word (e.g., "of", "the", "and", "for") are removed.
    - A final check ensures that the remaining candidates contain at least one significant word that is capitalized and identified by POS tagging as a potential part of a place name (e.g., Proper Noun, Noun).
- The identified place names are then highlighted in the original text and listed with their counts.
""")
