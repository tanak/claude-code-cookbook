# repair.py
import sys

# A list of encoding strategies to try for fixing mojibake.
# The script will attempt to use these encodings to reverse the corruption.
REPAIR_STRATEGIES = ['latin-1', 'mac_roman', 'cp1252', 'shift_jis', 'euc_jp']

def fix_file(filename):
    """
    Attempts to fix a file that was corrupted by being read with a wrong encoding
    and then saved as UTF-8. It iteratively applies repair strategies.
    """
    max_iterations = 5  # Limit to prevent infinite loops for very complex or unfixable cases
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        
        try:
            with open(filename, 'rb') as f:
                current_bytes = f.read()
        except IOError as e:
            print(f"Error reading file {filename}: {e}", file=sys.stderr)
            return

        # Assume the file is currently valid UTF-8 (but potentially garbled).
        # If it's not, it's likely a binary file or has another issue we can't fix.
        try:
            garbled_text = current_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # This is not a UTF-8 file, so we skip it silently.
            # Or, if it was previously repaired, it might now be truly binary.
            break # Exit if it's no longer valid UTF-8

        repaired_this_iteration = False
        for encoding_strategy in REPAIR_STRATEGIES:
            try:
                # Step 1: Reverse the garbling by encoding the text with the assumed wrong encoding.
                repaired_bytes = garbled_text.encode(encoding_strategy)

                # If the bytes are the same as the original, this strategy is not the correct one.
                if repaired_bytes == current_bytes:
                    continue

                # Step 2: Decode the result as UTF-8 to get the final, clean text.
                # If this fails, the repaired_bytes were not valid UTF-8, so the strategy was wrong.
                repaired_content = repaired_bytes.decode('utf-8')

                # If we get here, the repair was successful for this iteration.
                # Write the file and mark that a repair happened.
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(repaired_content)
                print(f"Successfully repaired {filename} (using {encoding_strategy}) in iteration {iterations}")
                repaired_this_iteration = True
                break # Break from inner loop to re-evaluate the file with the new content

            except (UnicodeEncodeError, UnicodeDecodeError):
                # This strategy failed. Silently continue to the next one.
                continue
            except IOError as e:
                # Handle potential errors during file writing.
                print(f"Error writing repaired file {filename}: {e}", file=sys.stderr)
                return
        
        if not repaired_this_iteration:
            # If no strategy worked in this iteration, we are done.
            break

    if iterations == max_iterations and repaired_this_iteration:
        print(f"Warning: Max iterations ({max_iterations}) reached for {filename}. May still be garbled.", file=sys.stderr)
    elif iterations == 1 and not repaired_this_iteration:
        print(f"No repair needed or possible for {filename}. (Already valid UTF-8 or unfixable)")
    else:
        print(f"Finished repairing {filename} after {iterations} iterations.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(0)  # Exit silently if no files are provided.
    
    for filename in sys.argv[1:]:
        fix_file(filename)
