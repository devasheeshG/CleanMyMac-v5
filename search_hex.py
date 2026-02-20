
import sys

def search_signatures(file_path):
    signatures = [
        b'\x55\x48\x89\xE5\x48\x8B\x35\xB2\xD0\x64\x00\xFF\x15\x1C\x5E\x55\x00\x31\xC9\x48\x85\xC0\x0F\x9E\xC1\x89\xC8\x5D\xC3',
        b'\x55\x48\x89\xE5\xE8\x77\x0E\x00\x00\x0F\xB6\xC0\x83\xE0\x01\x5D\xC3',
        b'\x55\x48\x89\xE5\x48\x8B\x35\x99\x15\x2E\x00\xFF\x15\x7B\x68\x27\x00\x31\xC9\x48\x85\xC0\x0F\x9E\xC1\x89\xC8\x5D\xC3'
    ]
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            for i, sig in enumerate(signatures):
                offset = content.find(sig)
                if offset != -1:
                    print(f"Signature {i+1} found at offset {hex(offset)}")
                else:
                    print(f"Signature {i+1} not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 search_hex.py <file_path>")
    else:
        search_signatures(sys.argv[1])
