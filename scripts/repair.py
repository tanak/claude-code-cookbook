# repair.py
import sys

def fix_file(filename):
    # Note: The user is on macOS, so the default file system encoding is likely UTF-8.
    # We read the file with 'utf-8' and see mojibake. This happens if UTF-8 bytes
    # were misinterpreted as a single-byte encoding like MacRoman or latin-1.
    # The most common variant of this mojibake is "double encoding" or
    # "UTF-8 interpreted as latin-1".

    try:
        with open(filename, 'rb') as f:
            corrupted_bytes = f.read()

        # The file was likely read as latin-1 (or similar), and then saved as UTF-8.
        # To reverse this, we must decode from UTF-8 (what it is now)
        # and then encode back to latin-1 to get the original byte sequence.
        original_bytes = corrupted_bytes.decode('utf-8').encode('latin-1')

        # Now we can decode the original bytes as UTF-8.
        repaired_content = original_bytes.decode('utf-8')

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(repaired_content)
        print(f"Successfully repaired {filename}")
    except Exception as e:
        # A common alternative is that it was misinterpreted as MacRoman
        try:
            original_bytes = corrupted_bytes.decode('utf-8').encode('mac_roman')
            repaired_content = original_bytes.decode('utf-8')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(repaired_content)
            print(f"Successfully repaired {filename} (using MacRoman fallback)")
        except Exception as e2:
            print(f"Failed to repair {filename}: latin-1 failed ({e}), mac_roman failed ({e2})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python repair.py <file1> <file2> ...")
        sys.exit(1)
    for filename in sys.argv[1:]:
        fix_file(filename)
