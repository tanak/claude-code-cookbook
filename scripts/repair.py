# repair.py
import sys

# A list of encoding strategies to try for fixing mojibake.
# The script will attempt to use these encodings to reverse the corruption.
REPAIR_STRATEGIES = ['latin-1', 'mac_roman']

def fix_file(filename):
    """
    Attempts to fix a file that was corrupted by being read with a wrong encoding
    and then saved as UTF-8.

    This refactored version iterates through a list of potential source encodings
    to make the code cleaner and more extensible.
    """
    try:
        with open(filename, 'rb') as f:
            original_bytes = f.read()
    except IOError as e:
        print(f"Error reading file {filename}: {e}", file=sys.stderr)
        return

    # The repair logic assumes the file is currently valid UTF-8 (but garbled).
    # If it's not, it's likely a binary file or has another issue we can't fix.
    try:
        garbled_text = original_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # This is not a UTF-8 file, so we skip it silently.
        return

    # Iterate through the defined strategies to find a fix.
    for encoding_strategy in REPAIR_STRATEGIES:
        try:
            # Step 1: Reverse the garbling by encoding the text with the assumed wrong encoding.
            repaired_bytes = garbled_text.encode(encoding_strategy)

            # If the bytes are the same as the original, this strategy is not the correct one.
            if repaired_bytes == original_bytes:
                continue

            # Step 2: Decode the result as UTF-8 to get the final, clean text.
            # If this fails, the repaired_bytes were not valid UTF-8, so the strategy was wrong.
            repaired_content = repaired_bytes.decode('utf-8')

            # Step 3: If we get here, the repair was successful. Write the file.
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(repaired_content)
            print(f"Successfully repaired {filename} (using {encoding_strategy})")
            return  # Exit after the first successful repair.

        except (UnicodeEncodeError, UnicodeDecodeError):
            # This strategy failed. Silently continue to the next one.
            continue
        except IOError as e:
            # Handle potential errors during file writing.
            print(f"Error writing repaired file {filename}: {e}", file=sys.stderr)
            return


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(0)  # Exit silently if no files are provided.
    
    for filename in sys.argv[1:]:
        fix_file(filename)
