import json
import re
import sys
from collections import defaultdict

from PyPDF2 import PdfReader

week_re = re.compile(r"V\.\s*(\d+)")
day_re = re.compile(r"^(Mån|Tis|Ons|Tor|Fre)\s+(\d+/\d+)\s+(.*)")

days_map = {
    "Mån": "Monday",
    "Tis": "Tuesday",
    "Ons": "Wednesday",
    "Tor": "Thursday",
    "Fre": "Friday",
}


def parse_pdf(path):
    text = ""
    reader = PdfReader(path)
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def parse_menu(text, year=2025):
    data = defaultdict(lambda: defaultdict(dict))
    current_week = None

    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Update week
        week_match = week_re.search(line)
        if week_match:
            current_week = int(week_match.group(1))
            continue

        # Parse day lines
        day_match = day_re.match(line)
        if day_match and current_week:
            day_sv, date_str, dish_text = day_match.groups()
            dish_text = re.sub(r"\s+", " ", dish_text)
            dish_text = re.sub(r"\s+([,:;])", r"\1", dish_text)
            dish_text = dish_text.strip()
            day_en = days_map[day_sv]
            data[str(year)][current_week][day_en] = dish_text

    return data


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python parse_menu.py input.pdf output.json")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    pdf_text = parse_pdf(input_path)
    parsed = parse_menu(pdf_text)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsed menu saved to {output_path}")
