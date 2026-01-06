
from __future__ import annotations

import argparse, concurrent.futures as cf, hashlib, logging, re, sys, time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS  # pip install ddgs


DEFAULT_DOMAINS = [
    # Core ELISA kit vendors / manufacturers
    "fn-test.com",            # FineTest
    "novusbio.com",           # Novus / Bio-Techne family listings
    "krishgen.com",           # Krishgen
    "novateinbio.com",        # Novatein
    "rndsystems.com",         # R&D Systems (Bio-Techne)
    "bio-techne.com",         # Bio-Techne
    "abcam.com",              # Abcam
    "thermofisher.com",       # Thermo Fisher / Invitrogen
    "sigmaaldrich.com",       # Sigma-Aldrich / Merck
    "merckmillipore.com",     # Merck Millipore
    "mybiosource.com",        # MyBioSource
    "antibodies-online.com",  # Aggregator
    "lsbio.com",              # LSBio
    "assaygenie.com",         # AssayGenie
    "cloud-clone.com",        # Cloud-Clone
    "cusabio.com",            # CUSABIO
    "elabscience.com",        # Elabscience
    "biomatik.com",           # Biomatik
    "lifespanbio.com",        # Lifespan Biosciences
    "sino-biological.com",    # Sino Biological
    "raybiotech.com",         # RayBiotech
    "bosterbio.com",          # BosterBio
    "genetex.com",            # GeneTex
    # Distributors python elisa_matcher.py --early-stop --site-results 20 --max-fetch 70
    "fishersci.com",
    "vwr.com",
]


def vendor(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")

def sid(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def species_ok(text: str, species: str) -> bool:
    s = species.strip().lower()
    if not s:
        return True
    t = text.lower()
    return (s in t) or (s == "mouse" and ("mus musculus" in t or "mice" in t))

def samples_ok(text: str, sample_terms: List[str]) -> bool:
    if not sample_terms:
        return True
    t = text.lower()
    return any(st.lower() in t for st in sample_terms)

def detect_analyte(blob: str, analytes: List[str], aliases: Dict[str, List[str]]) -> Optional[str]:
    up = blob.upper()
    for a in analytes:
        if re.search(rf"\b{re.escape(a.upper())}\b", up):
            return a
    for canon, alist in aliases.items():
        if canon not in analytes:
            continue
        for al in alist:
            if re.search(rf"\b{re.escape(al.upper())}\b", up):
                return canon
    return None

def ddg_search(query: str, max_results: int) -> List[dict]:
    out: List[dict] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            out.append(r)
    return out

def to_urls(results: List[dict], allow_domains: Optional[Set[str]]) -> List[str]:
    urls: List[str] = []
    for r in results:
        u = r.get("href") or r.get("url") or ""
        if not u.startswith(("http://", "https://")):
            continue
        dom = vendor(u)
        if allow_domains and not (dom in allow_domains or any(dom.endswith("." + d) for d in allow_domains)):
            continue
        urls.append(u)
    return urls

def fetch_page(url: str, session: requests.Session, timeout: int, ua: str) -> Optional[tuple[str, str, str]]:
    try:
        r = session.get(url, headers={"User-Agent": ua}, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        title = norm(soup.title.text) if soup.title and soup.title.text else ""
        text = norm(soup.get_text(" "))
        return url, r.url, title + "\n" + text
    except Exception:
        return None


@dataclass
class PageHit:
    final_url: str
    vendor: str
    analyte: str
    title: str
    species_found: bool
    samples_found: bool
    has_elisa: bool


def keep(ph: PageHit, require_species: bool, require_samples: bool, require_elisa: bool) -> bool:
    if require_species and not ph.species_found:
        return False
    if require_samples and not ph.samples_found:
        return False
    if require_elisa and not ph.has_elisa:
        return False
    return True

def match_by_vendor(pagehits: List[PageHit], analytes: List[str]) -> Dict[str, Dict[str, List[PageHit]]]:
    out: Dict[str, Dict[str, List[PageHit]]] = {}
    for ph in pagehits:
        out.setdefault(ph.vendor, {a: [] for a in analytes})
        out[ph.vendor][ph.analyte].append(ph)
    return {v: d for v, d in out.items() if all(d[a] for a in analytes)}

def setup_logger(level: str) -> logging.Logger:
    logger = logging.getLogger("elisa_matcher")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(h)
    return logger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analytes", nargs="+", default=["NOX4", "CXCL10"])
    ap.add_argument("--species", default="mouse")
    ap.add_argument("--sample", nargs="*", default=["serum", "plasma"])

    ap.add_argument("--domains", nargs="*", default=None, help="Override domain list.")
    ap.add_argument("--discover-domains", action="store_true", help="Web-wide domain discovery (ignores DEFAULT_DOMAINS).")

    ap.add_argument("--seed-results", type=int, default=30)
    ap.add_argument("--site-results", type=int, default=20)

    ap.add_argument("--max-fetch", type=int, default=60)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--timeout", type=int, default=12)
    ap.add_argument("--budget-sec", type=int, default=40)
    ap.add_argument("--ua", default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36")

    ap.add_argument("--require-species", action="store_true")
    ap.add_argument("--require-samples", action="store_true")
    ap.add_argument("--require-elisa", action="store_true")

    ap.add_argument("--early-stop", action="store_true")
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    logger = setup_logger(args.log_level)

    start = time.time()
    def timed_out() -> bool:
        return (time.time() - start) > args.budget_sec

    analytes = [a.strip() for a in args.analytes if a.strip()]
    if len(analytes) < 2:
        raise SystemExit("Need >=2 analytes")

    aliases = {"CXCL10": ["IP-10", "IP10", "CRG-2", "CRG2", "INTERFERON GAMMA INDUCED PROTEIN 10"]}

    allow_domains: Optional[Set[str]] = None
    if args.discover_domains:
        allow_domains = None
        logger.info("Mode: discover domains (web-wide).")
    elif args.domains:
        allow_domains = set(d.lower().replace("www.", "") for d in args.domains)
        logger.info(f"Mode: custom domains ({len(allow_domains)}).")
    else:
        allow_domains = set(DEFAULT_DOMAINS)
        logger.info(f"Mode: default domains ({len(allow_domains)}).")

    if args.discover_domains:
        logger.info("Discovering domains...")
        discovered: Set[str] = set()
        for a in analytes:
            if timed_out():
                break
            res = ddg_search(f"{args.species} {a} ELISA kit", args.seed_results)
            for u in to_urls(res, None):
                discovered.add(vendor(u))
        allow_domains = discovered if discovered else None
        logger.info(f"Discovered domains: {0 if allow_domains is None else len(allow_domains)}")

    candidates: List[str] = []
    seen: Set[str] = set()

    def add(urls: Iterable[str]):
        for u in urls:
            k = sid(u)
            if k in seen:
                continue
            seen.add(k)
            candidates.append(u)
            if len(candidates) >= args.max_fetch:
                break

    logger.info("Collecting URLs...")
    for a in analytes:
        if timed_out() or len(candidates) >= args.max_fetch:
            break
        res = ddg_search(f"{args.species} {a} ELISA kit", min(args.seed_results, 25))
        add(to_urls(res, allow_domains))

    if allow_domains:
        for d in list(allow_domains):
            if timed_out() or len(candidates) >= args.max_fetch:
                break
            for a in analytes:
                if timed_out() or len(candidates) >= args.max_fetch:
                    break
                res = ddg_search(f"site:{d} {a} ELISA kit {args.species}", args.site_results)
                add(to_urls(res, allow_domains))

    logger.info(f"URLs: {len(candidates)}")

    session = requests.Session()
    pagehits: List[PageHit] = []

    def worker(u: str) -> Optional[PageHit]:
        if timed_out():
            return None
        got = fetch_page(u, session, args.timeout, args.ua)
        if not got:
            return None
        _, final_url, title_and_text = got
        title, _, text = title_and_text.partition("\n")
        blob = f"{title} {text} {final_url}"
        a = detect_analyte(blob, analytes, aliases)
        if not a:
            return None
        ph = PageHit(
            final_url=final_url,
            vendor=vendor(final_url),
            analyte=a,
            title=title,
            species_found=species_ok(text, args.species),
            samples_found=samples_ok(text, args.sample),
            has_elisa=("elisa" in text.lower()),
        )
        return ph if keep(ph, args.require_species, args.require_samples, args.require_elisa) else None

    logger.info("Fetching...")
    matched_any: Dict[str, Dict[str, List[PageHit]]] = {}

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(worker, u) for u in candidates]
        for f in cf.as_completed(futs):
            if timed_out():
                break
            try:
                ph = f.result()
            except Exception:
                ph = None
            if not ph:
                continue
            pagehits.append(ph)

            if args.early_stop:
                matched_any = match_by_vendor(pagehits, analytes)
                if matched_any:
                    break

    matched = matched_any if matched_any else match_by_vendor(pagehits, analytes)
    if not matched:
        logger.info("No matches.")
        return

    print("\n=== MATCHED ===")
    for v, d in matched.items():
        print(f"\n{v}")
        for a in analytes:
            print(f"  {a}: {d[a][0].final_url}")


if __name__ == "__main__":
    main()
