import sys
from .db import override_item

def main():
    if len(sys.argv) != 4:
        print("Usage: python override_item.py <item> <category> <normalized_name>")
        sys.exit(1)

    item = sys.argv[1]
    category = sys.argv[2]
    normalized_name = sys.argv[3]

    override_item(item, category, normalized_name)
    print(f"Override saved: {item} → {category} ({normalized_name})")

if __name__ == "__main__":
    main()
