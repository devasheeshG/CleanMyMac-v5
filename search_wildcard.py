
import sys
import re

def search_wildcard(file_path, hex_pattern):
    # Convert hex pattern with ?? to regex
    regex_pattern = re.escape(bytes.fromhex(hex_pattern.replace('??', '00')))
    regex_pattern = regex_pattern.replace(b'\\x00', b'.')
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            matches = list(re.finditer(regex_pattern, content))
            if matches:
                for match in matches:
                    print(f"Match found at offset {hex(match.start())}")
                    # Print context
                    context = content[max(0, match.start()):min(len(content), match.end())]
                    print(f"Bytes: {context.hex()}")
            else:
                print("No matches found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 search_wildcard.py <file_path> <hex_pattern_with_??>")
    else:
        search_wildcard(sys.argv[1], sys.argv[2])
