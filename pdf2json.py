#!/usr/bin/env python3
import sys, re, zlib, json


def load_pdf(path):
    clean = path.strip().strip("'\"")
    with open(clean, "rb") as f:
        return f.read()


def parse_objects(pdf_bytes):
    pattern = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.S)
    objs = {}
    for m in pattern.finditer(pdf_bytes):
        key = f"{m.group(1).decode()} {m.group(2).decode()}"
        objs[key] = m.group(3).strip()
    return objs


def decompress_stream(obj_bytes):
    hdr, sep, tail = obj_bytes.partition(b"stream")
    if not sep:
        return None
    data, _, _ = tail.lstrip(b"\r\n").partition(b"endstream")
    if b"/FlateDecode" in hdr:
        try:
            return zlib.decompress(data)
        except:
            return None
    return data


def extract_text_from_stream(stream_bytes):
    # Pull out all (…) literals and decode with Windows-1252
    texts = re.findall(rb"\((.*?)\)", stream_bytes, re.S)
    # cp1252 maps 0xF6→“ö” etc., and never throws on any byte
    return "".join(t.decode("cp1252", errors="ignore") for t in texts)


def build_page_texts(objs):
    page_re = re.compile(rb"/Type\s*/Page.*?/Contents\s+(\d+\s+\d+\s+R)", re.S)
    pages = []
    for i, (obj_id, data) in enumerate(objs.items(), start=1):
        if b"/Type" in data and b"/Page" in data:
            m = page_re.search(data)
            if not m:
                continue
            ref = m.group(1).decode()  # e.g. "5 0 R"
            key = ref.rsplit(" ", 1)[0]  # → "5 0"
            stream = decompress_stream(objs.get(key, b""))
            text = extract_text_from_stream(stream) if stream else ""
            pages.append({"page_number": i, "text": text})
    return pages


def manual_pdf_to_json(in_pdf, out_json):
    pdf_bytes = load_pdf(in_pdf)
    objs = parse_objects(pdf_bytes)
    pages = build_page_texts(objs)
    out_path = out_json.strip().strip("'\"")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"pages": pages}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(pages)} pages to '{out_path}'")


def main():
    if len(sys.argv) == 3:
        in_pdf, out_json = sys.argv[1], sys.argv[2]
    else:
        print("Expected two args (input.pdf output.json).")
        in_pdf = input("PDF path: ").strip()
        out_json = input("JSON path: ").strip()
    manual_pdf_to_json(in_pdf, out_json)


if __name__ == "__main__":
    main()
