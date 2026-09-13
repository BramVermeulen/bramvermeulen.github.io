#!/usr/bin/env python3
"""Assert the built site keeps the promises its source makes.

Reads dist/ -- the exact directory that gets published -- so a regression in a
template, a data file or an integration fails the build before GitHub Pages
sees it. Standard library only: this has to run on a bare runner's python3,
with no pip install and no npm dependency to keep current.

Usage: python3 scripts/check-build.py [dist-dir]
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# Asset prefixes the pages are allowed to point at; each must exist in dist.
ASSET_PREFIXES = ("/_astro/", "/fonts/", "/favicon", "/og-image", "/apple-touch-icon")
# The JSON-LD node types every page of a kind has to carry.
EXPECTED_LD_TYPES = {
    "/": {"Person", "WebSite", "ProfilePage"},
    "/projects/portfolio/": {"Person", "WebSite", "BreadcrumbList", "SoftwareSourceCode"},
}

violations = []


def fail(where, message):
    violations.append(f"{where}: {message}")


def read_site():
    """The canonical origin, taken from astro.config.mjs so it cannot drift."""
    config = (ROOT / "astro.config.mjs").read_text()
    match = re.search(r"site:\s*['\"]([^'\"]+)['\"]", config)
    if not match:
        sys.exit("check-build: no `site` found in astro.config.mjs")
    return match.group(1).rstrip("/")


def read_indexnow_key():
    """The IndexNow key the deploy workflow pings with."""
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text()
    match = re.search(r"^\s*KEY:\s*([0-9a-f]{8,})\s*$", workflow, re.M)
    if not match:
        sys.exit("check-build: no IndexNow KEY found in .github/workflows/deploy.yml")
    return match.group(1)


class Page(HTMLParser):
    """Everything the checks need from one HTML file, in a single pass."""

    def __init__(self, path, url):
        super().__init__(convert_charrefs=True)
        self.path, self.url = path, url
        self.elements = []  # (tag, attrs, in_head)
        self.ids, self.ld_json, self.titles = set(), [], []
        self.h1_count = 0
        self._in_head = self._in_title = False
        self._in_ld = False
        self._anchor_depth = 0
        self.nested_anchors = 0
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = {k: (v if v is not None else "") for k, v in attrs}
        self.elements.append((tag, attrs, self._in_head))
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "head":
            self._in_head = True
        elif tag == "title":
            self._in_title = True
            self.titles.append("")
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a":
            self._anchor_depth += 1
            if self._anchor_depth > 1:
                self.nested_anchors += 1
        elif tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_ld = True
            self.ld_json.append("")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
        elif tag == "title":
            self._in_title = False
        elif tag == "a":
            self._anchor_depth = max(0, self._anchor_depth - 1)
        elif tag == "script":
            self._in_ld = False

    def handle_data(self, data):
        if self._in_title and self.titles:
            self.titles[-1] += data
        if self._in_ld and self.ld_json:
            self.ld_json[-1] += data

    def find(self, tag, **match):
        return [
            attrs
            for name, attrs, _ in self.elements
            if name == tag and all(attrs.get(k) == v for k, v in match.items())
        ]

    def meta(self, **match):
        return [a.get("content", "") for a in self.find("meta", **match)]


def page_url(path, dist):
    """dist/index.html -> /, dist/x/index.html -> /x/, dist/404.html -> /404/."""
    rel = path.relative_to(dist)
    parts = list(rel.parts[:-1]) + ([] if rel.name == "index.html" else [rel.stem])
    return "/" + "".join(f"{p}/" for p in parts)


def resolve(dist, url_path):
    """A site path -> the file serving it, directory format included."""
    rel = url_path.strip("/")
    for candidate in (dist / rel / "index.html", dist / f"{rel}.html", dist / rel):
        if candidate.is_file():
            return candidate
    return None


def check_head(page, site):
    """Title, description, canonical, social cards, lang, single h1."""
    where = page.path
    if len(page.titles) != 1 or not page.titles[0].strip():
        fail(where, f"expected exactly one non-empty <title>, found {len(page.titles)}")
    descriptions = [d for d in page.meta(name="description") if d.strip()]
    if len(descriptions) != 1:
        fail(where, f"expected one non-empty meta description, found {len(descriptions)}")

    canonicals = [a.get("href", "") for a in page.find("link", rel="canonical")]
    expected = site + page.url
    if canonicals != [expected]:
        fail(where, f"canonical should be [{expected}], found {canonicals}")

    for prop in ("og:title", "og:description", "og:image"):
        values = [v for v in page.meta(property=prop) if v.strip()]
        if not values:
            fail(where, f"missing {prop}")
        elif prop == "og:image" and not values[0].startswith("https://"):
            fail(where, f"og:image must be absolute, found {values[0]!r}")
    if not any(v.strip() for v in page.meta(name="twitter:card")):
        fail(where, "missing twitter:card")

    html_tags = page.find("html")
    if not html_tags or not html_tags[0].get("lang", "").strip():
        fail(where, "<html> is missing a lang attribute")
    if page.h1_count != 1:
        fail(where, f"expected exactly one <h1>, found {page.h1_count}")


def check_json_ld(page, dates):
    """Structured data: the promised nodes, resolvable @id refs, one date."""
    where = page.path
    expected = EXPECTED_LD_TYPES.get(page.url, set())
    if not expected and page.ld_json:
        fail(where, f"expected no JSON-LD here, found {len(page.ld_json)} block(s)")

    defined, referenced, types = set(), [], set()

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            if set(node) == {"@id"}:
                referenced.append(node["@id"])
            elif "@id" in node:
                defined.add(node["@id"])
            node_type = node.get("@type")
            types.update([node_type] if isinstance(node_type, str) else node_type or [])
            if "dateModified" in node:
                dates[node["dateModified"]].add(str(where))
            for value in node.values():
                walk(value)

    for block in page.ld_json:
        try:
            data = json.loads(block)
        except json.JSONDecodeError as error:
            fail(where, f"JSON-LD does not parse: {error}")
            continue
        if expected and "@graph" not in data:
            fail(where, "JSON-LD should be a single @graph document")
        walk(data)

    missing = expected - types
    if missing:
        fail(where, f"JSON-LD is missing node type(s) {sorted(missing)}")
    for ref in set(referenced) - defined:
        fail(where, f"JSON-LD @id reference {ref!r} resolves to nothing in this document")

    if "Person" in expected:
        for block in page.ld_json:
            for node in json.loads(block).get("@graph", []):
                if node.get("@type") != "Person":
                    continue
                if not str(node.get("@id", "")).endswith("#person"):
                    fail(where, f"Person @id should end in #person, found {node.get('@id')!r}")
                if not node.get("name"):
                    fail(where, "Person is missing a name")
                for field in ("sameAs", "knowsAbout"):
                    if not isinstance(node.get(field), list) or not node[field]:
                        fail(where, f"Person.{field} should be a non-empty list")


def check_links(page, pages, dist):
    """Outbound safety, no nested anchors, and every internal target exists."""
    where = page.path
    if page.nested_anchors:
        fail(where, f"found {page.nested_anchors} nested <a> element(s)")

    for attrs in page.find("a"):
        href = attrs.get("href", "").strip()
        if not href or href.startswith(("mailto:", "tel:")):
            continue
        rel = attrs.get("rel", "").split()
        external = href.startswith(("http://", "https://"))
        if external:
            if attrs.get("target") != "_blank":
                fail(where, f"external link {href} should open in a new tab")
            if "noopener" not in rel:
                fail(where, f"external link {href} is missing rel=noopener")
            continue
        if attrs.get("target") == "_blank":
            fail(where, f"internal link {href} should not open in a new tab")

        path_part, _, fragment = href.partition("#")
        if not path_part:
            target = page
        else:
            url = path_part if path_part.startswith("/") else page.url + path_part
            resolved = resolve(dist, url)
            if resolved is None:
                fail(where, f"internal link {href} resolves to no file in dist")
                continue
            target = pages[resolved]
        if fragment and fragment not in target.ids:
            fail(where, f"internal link {href} points at no element id in {target.path}")


def check_assets(page, dist, site):
    """Inline graphics carry intrinsic size; referenced files really exist."""
    where = page.path
    for tag, attrs, _ in page.elements:
        if tag == "svg" and not (attrs.get("width") and attrs.get("height")):
            fail(where, "an <svg> is missing width/height")
        if tag == "img":
            missing = [a for a in ("width", "height") if not attrs.get(a)]
            if "alt" not in attrs:
                missing.append("alt")
            if missing:
                fail(where, f"<img src={attrs.get('src')!r}> is missing {missing}")

    references = [a.get(k, "") for _, a, _ in page.elements for k in ("href", "src")]
    references += page.meta(property="og:image")
    for ref in references:
        local = ref[len(site) :] if ref.startswith(site) else ref
        if local.startswith(ASSET_PREFIXES) and not (dist / local.lstrip("/")).is_file():
            fail(where, f"asset {ref} is referenced but missing from dist")

    icons = [a for a in page.find("link") if "icon" in a.get("rel", "").split()]
    if not any(a.get("type") == "image/svg+xml" for a in icons):
        fail(where, "no svg favicon link in <head>")
    if not any(a.get("href", "").endswith(".ico") for a in icons):
        fail(where, "no .ico favicon fallback in <head>")


def check_site_files(dist, site, urls):
    """Sitemap, robots.txt and the IndexNow ownership key."""
    sitemap = dist / "sitemap-0.xml"
    if not sitemap.is_file():
        fail(sitemap, "missing from dist")
    else:
        entries = {
            url.findtext(f"{SITEMAP_NS}loc"): url.findtext(f"{SITEMAP_NS}lastmod")
            for url in ET.parse(sitemap).getroot()
        }
        expected = {site + url for url in urls}
        if set(entries) != expected:
            fail(sitemap, f"expected exactly {sorted(expected)}, found {sorted(entries)}")
        for loc, lastmod in entries.items():
            if not lastmod:
                fail(sitemap, f"{loc} has no <lastmod>")

    robots = dist / "robots.txt"
    if not robots.is_file():
        fail(robots, "missing from dist")
    elif "sitemap-index.xml" not in robots.read_text():
        fail(robots, "does not point at the sitemap index")

    key = read_indexnow_key()
    key_file = dist / f"{key}.txt"
    if not key_file.is_file():
        fail(key_file, "IndexNow key file missing from dist")
    elif key_file.read_text().strip() != key:
        fail(key_file, "IndexNow key file does not contain exactly the key")


def main():
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "dist").resolve()
    site = read_site()
    html_files = sorted(dist.rglob("*.html"))
    if not html_files:
        sys.exit(f"check-build: no HTML found in {dist} -- was the site built?")

    pages = {path: Page(path, page_url(path, dist)) for path in html_files}
    dates = defaultdict(set)
    for page in pages.values():
        check_head(page, site)
        check_json_ld(page, dates)
        check_links(page, pages, dist)
        check_assets(page, dist, site)

    # Two pages sharing a title or a description are two pages competing for
    # the same search result, so treat a duplicate as a build failure.
    fields = {
        "title": lambda p: p.titles,
        "description": lambda p: p.meta(name="description"),
    }
    for field, getter in fields.items():
        seen = defaultdict(list)
        for page in pages.values():
            for value in getter(page)[:1]:
                seen[value.strip()].append(str(page.path))
        for value, owners in seen.items():
            if len(owners) > 1:
                fail(", ".join(owners), f"share the same {field} {value!r}")

    if len(dates) > 1:
        fail(dist, f"dateModified differs across the build: {dict(dates)}")

    # Only the real pages belong in the sitemap; 404 must stay out of it.
    indexable = sorted(p.url for p in pages.values() if p.url != "/404/")
    check_site_files(dist, site, indexable)

    if violations:
        print(f"check-build: {len(violations)} violation(s) in {dist}\n", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        sys.exit(1)

    svgs = sum(1 for p in pages.values() for tag, _, _ in p.elements if tag == "svg")
    links = sum(len(p.find("a")) for p in pages.values())
    blocks = sum(len(p.ld_json) for p in pages.values())
    print(
        f"check-build: {len(pages)} pages, {links} links, {svgs} svgs, "
        f"{blocks} JSON-LD blocks, {len(indexable)} sitemap entries -- all checks passed"
    )


if __name__ == "__main__":
    main()
