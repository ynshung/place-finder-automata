import streamlit as st
from PlaceFinder.PlaceFinder import PlaceFinder # Assuming PlaceFinder.py is in the same directory
import pandas as pd # Import pandas for DataFrame
from annotated_text import annotated_text # Import annotated_text

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
            st.subheader("Identified Place Candidates & Counts:")
            for place, count in results.items():
                st.write(f"- **{place}**: {count}")
        else:
            st.write("No place candidates found.")

        with st.expander("View Part-of-Speech Tags"):
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


        with st.expander("View DFA State Transitions Log"):
            st.subheader("DFA Processing Log")
            
            # Filter logs for token processing and state changes
            transition_logs = [
                log for log in logs 
                if "token" in log and "prev_state" in log and "new_state" in log and "action" in log
            ]
            
            if transition_logs:
                # Convert to DataFrame for better display
                df_transitions = pd.DataFrame(transition_logs)
                # Select and reorder columns for clarity
                df_display = df_transitions[["token", "tag", "prev_state", "action", "new_state", "buffer_after_action"]]
                df_display.columns = ["Token", "POS Tag", "Previous State", "Action/Details", "New State", "Buffer Content"]
                st.dataframe(df_display, use_container_width=True) # Set use_container_width to True
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
