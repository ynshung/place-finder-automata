import PlaceFinder.PlaceFinder as PlaceFinder

paragraph = """
Malaysia is a federal constitutional monarchy located in Southeast Asia. It consists of thirteen states
and three federal territories and has a total landmass of 329,847 square kilometres (127,350 sq mi)
separated by the South China Sea into two similarly sized regions, Peninsular Malaysia and East
Malaysia (Malaysian Borneo). Peninsular Malaysia shares a land and maritime border with Thailand
and maritime borders with Singapore, Vietnam, and Indonesia. East Malaysia shares land and
maritime borders with Brunei and Indonesia and a maritime border with the Philippines. The capital
city is Kuala Lumpur, while Putrajaya is the seat of the federal government. By 2015, with a population
of over 30 million, Malaysia became 43rd most populous country in the world. The southernmost
point of continental Eurasia, Tanjung Piai, is in Malaysia, located in the tropics. It is one of 17
megadiverse countries on earth, with large numbers of endemic species.
Malaysia has its origins in the Malay kingdoms present in the area which, from the 18th century,
became subject to the British Empire. The first British territories were known as the Straits
Settlements, whose establishment was followed by the Malay kingdoms becoming British
protectorates. The territories on Peninsular Malaysia were first unified as the Malayan Union in 1946.
Malaya was restructured as the Federation of Malaya in 1948, and achieved independence on 31
August 1957. Malaya united with North Borneo, Sarawak, and Singapore on 16 September 1963, with
is being added to give the new country the name Malaysia. Less than two years later in 1965,
Singapore was expelled from the federation.
Since its independence, Malaysia has had one of the best economic records in Asia, with its GDP
growing at an average of 6.5% per annum for almost 50 years. The economy has traditionally been
fuelled by its natural resources, but is expanding in the sectors of science, tourism, commerce and
medical tourism. Today, Malaysia has a newly industrialised market economy, ranked third largest in
Southeast Asia and 29th largest in the world. It is a founding member of the Association of Southeast
Asian Nations, the East Asia Summit and the Organisation of Islamic Cooperation, and a member of
Asia-Pacific Economic Cooperation, the Commonwealth of Nations, and the Non-Aligned Movement.
"""

with open("output.txt", "w", encoding="utf-8") as output_file:
    finder = PlaceFinder.PlaceFinder()
    places = finder.find_places(paragraph)
    logs = finder.get_logs()

    output_file.write("Identified Place Names and Occurrences:\n")
    if places:
        for place, count in places.items():
            output_file.write(f"- {place}: {count}\n")
    else:
        output_file.write("No place names identified.\n")

    output_file.write("\n\n--- Processing Logs ---\n")
    
    dfa_log_header = f"{'Token':<25} | {'Tag':<8} | {'Prev State':<20} | {'New State':<20} | {'Buffer':<40} | {'Action':<70}"
    dfa_log_header_written = False
    post_processing_logs_started = False

    for log_entry in logs:
        if isinstance(log_entry, dict) and "event" in log_entry:
            event_type = log_entry["event"]
            if event_type == "Preprocessing":
                if dfa_log_header_written: # Newline if DFA table was being printed
                    output_file.write("\n")
                    dfa_log_header_written = False
                output_file.write(f"\nEvent: {log_entry['event']}\n")
                output_file.write(f"Details: {log_entry['details']}\n")
                output_file.write("POS Tags (line by line):\n")
                for line_tags in log_entry['tags_by_line']:
                    if line_tags:
                        # Apply symbol exclusion for POS tagging
                        formatted_parts = []
                        for token, tag in line_tags:
                            # Define symbols that should not be tagged
                            if token in ['.', ',', '(', ')', '[', ']', '{', '}', ':', ';', '"', "'", '!', '?', '-', '--']:
                                formatted_parts.append(token)
                            else:
                                formatted_parts.append(f"{token} ({tag})")
                        tagged_sentence = " ".join(formatted_parts)
                        output_file.write(f"  {tagged_sentence}\n")
                    else:
                        output_file.write("\n") # Preserve empty lines
            elif event_type in ["PostProcessingStart", "PostProcessFilter", "PostProcessingEnd"]:
                if dfa_log_header_written: # End DFA table before post-processing logs
                    output_file.write("\n")
                    dfa_log_header_written = False
                if not post_processing_logs_started:
                    output_file.write("\nPost-Processing Details:\n")
                    output_file.write("-" * 30 + "\n")
                    post_processing_logs_started = True
                if event_type == "PostProcessingStart":
                    output_file.write(f"Raw candidates: {log_entry['detail']}\n")
                elif event_type == "PostProcessFilter":
                    output_file.write(f"Filtered: '{log_entry['candidate']}' - Type: {log_entry['filter_type']} - Reason: {log_entry['detail']}\n")
                elif event_type == "PostProcessingEnd":
                    output_file.write(f"Final candidates with counts: {log_entry['final_candidates_counts']}\n")
            # This else implies it's a DFA step log (token-based)
            else: 
                # This case should not be reached if all dict logs have an 'event' key
                # If it's a DFA step, it should not have an 'event' key based on new PlaceFinder structure
                # This block is a fallback or for unexpected dict log entries.
                output_file.write(f"Generic Log Entry: {log_entry}\n")

        elif isinstance(log_entry, dict) and "token" in log_entry: # DFA step log
            if not dfa_log_header_written:
                output_file.write("\nToken-based DFA State Transitions:\n")
                output_file.write(dfa_log_header + "\n")
                output_file.write("-" * len(dfa_log_header) + "\n")
                dfa_log_header_written = True
                post_processing_logs_started = False # Reset if we are back to DFA logs

            token_val = log_entry['token']
            tag_val = log_entry['tag']
            prev_state_val = log_entry['prev_state']
            action_val = log_entry['action']
            new_state_val = log_entry['new_state']
            buffer_val = log_entry['buffer_after_action']
            
            token_display = (token_val[:22] + '...') if len(token_val) > 25 else token_val
            buffer_display = (buffer_val[:37] + '...') if len(buffer_val) > 40 else buffer_val
            action_display = (action_val[:67] + '...') if len(action_val) > 70 else action_val

            output_file.write(
                f"{token_display:<25} | {tag_val:<8} | {prev_state_val:<20} | {new_state_val:<20} | {buffer_display:<40} | {action_display:<70}\n"
            )
        else:
             # Fallback for any other type of log entry (e.g. old string-based logs if any)
            if dfa_log_header_written:
                output_file.write("\n")
                dfa_log_header_written = False
            output_file.write(f"Other Log: {log_entry}\n")
