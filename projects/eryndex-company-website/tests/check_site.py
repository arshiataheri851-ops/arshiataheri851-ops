from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]


class PageAudit(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.references = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        for attribute in ("href", "src"):
            value = values.get(attribute, "").strip()
            if value:
                self.references.append((tag, attribute, value))


def audit():
    errors = []
    pages = sorted(ROOT.rglob("*.html"))
    if not pages:
        return ["No HTML pages found"]

    audits = {}
    for page in pages:
        parser = PageAudit()
        parser.feed(page.read_text(encoding="utf-8"))
        parser.close()
        audits[page] = parser

    for page, parser in audits.items():
        for tag, attribute, reference in parser.references:
            parsed = urlparse(reference)
            if parsed.scheme or parsed.netloc or reference.startswith("//"):
                continue

            raw_path = unquote(parsed.path)
            target = (page.parent / raw_path).resolve() if raw_path else page.resolve()
            if target.is_dir():
                target = target / "index.html"
            elif not target.exists() and not target.suffix:
                directory_index = target / "index.html"
                if directory_index.exists():
                    target = directory_index

            if not target.exists() or not target.is_file():
                errors.append(f"{page.relative_to(ROOT)}: broken {attribute}={reference!r}")
                continue

            if parsed.fragment and target.suffix.lower() == ".html":
                target_page = next((candidate for candidate in audits if candidate.resolve() == target.resolve()), None)
                if target_page is not None and unquote(parsed.fragment) not in audits[target_page].ids:
                    errors.append(f"{page.relative_to(ROOT)}: missing anchor #{parsed.fragment} in {target.relative_to(ROOT)}")

    return errors


if __name__ == "__main__":
    problems = audit()
    if problems:
        print("\\n".join(problems))
        raise SystemExit(1)
    print(f"Checked {len(list(ROOT.rglob('*.html')))} HTML pages: all local links, assets and anchors resolve.")
